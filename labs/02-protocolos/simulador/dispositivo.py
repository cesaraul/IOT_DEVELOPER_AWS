"""Dispositivo IoT simulado: el mismo sensor hablando por HTTP y por MQTT.

Lee una muestra (temperatura y nivel) y la manda por los dos caminos a la vez.
Es el corazón del laboratorio: todo lo que ves en la interfaz sale de aquí.

Cada canal tiene su propio intervalo y su propia forma de recibir órdenes:

  HTTP : pregunta cada POLL_CONFIG_S segundos con GET /config  -> *polling*
  MQTT : está suscrito al topic de comandos                    -> *push*

Léelo entero: es el mismo código que escribes tú en los laboratorios L3 (HTTP)
y L2–L4 (MQTT), solo que con los dos juntos para poder compararlos.
"""

from __future__ import annotations

import json
import os
import random
import threading
import time

import paho.mqtt.client as mqtt
import requests

API = os.getenv("API_URL", "http://localhost:8000")
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PUERTO = int(os.getenv("MQTT_PORT", "1883"))
ID = os.getenv("DISPOSITIVO_ID", "tanque-03")
POLL_CONFIG_S = float(os.getenv("POLL_CONFIG_S", "15"))

BASE = f"fablab/planta1/{ID}"
T_TELEMETRIA = f"{BASE}/telemetria"
T_ESTADO = f"{BASE}/estado"
T_COMANDOS = f"{BASE}/comandos"
T_ACK = f"{BASE}/ack"

CABECERAS = {"Authorization": "Bearer demo-key", "Content-Type": "application/json"}


class Dispositivo:
    def __init__(self) -> None:
        self.intervalo_http = 5.0
        self.intervalo_mqtt = 5.0
        self.version_config = 0
        self.red_caida = False
        self.cola: list[dict] = []          # muestras HTTP sin enviar (lab L3)
        self.sesion = requests.Session()    # reutiliza la conexión TCP
        self.mqtt_vivo = False
        self.cliente = self._crear_cliente_mqtt()

    # -- utilidades -------------------------------------------------------

    def contar(self, texto: str, nivel: str = "info", reintento: bool = False,
               protocolo: str = "http") -> None:
        """Le cuenta a la interfaz lo que está pasando (canal fuera de banda)."""
        print(f"[{nivel}] {texto}", flush=True)
        try:
            self.sesion.post(
                f"{API}/sim/evento",
                json={"texto": texto, "nivel": nivel, "reintento": reintento,
                      "protocolo": protocolo},
                timeout=3,
            )
        except requests.RequestException:
            pass

    def leer_sensor(self) -> dict:
        return {
            "temp": round(random.uniform(18, 36), 1),
            "nivel": random.randint(0, 100),
            "ts": round(time.time(), 1),
        }

    # -- MQTT -------------------------------------------------------------

    def _crear_cliente_mqtt(self) -> mqtt.Client:
        cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=ID)
        # TESTAMENTO: si esta conexión muere sin despedirse, el broker publica
        # "offline" por nosotros. Se entrega ANTES de conectar.
        cliente.will_set(T_ESTADO, "offline", qos=1, retain=True)
        cliente.on_connect = self._al_conectar
        cliente.on_message = self._al_recibir
        return cliente

    def _al_conectar(self, cliente, userdata, flags, codigo, propiedades=None):
        self.mqtt_vivo = True
        # Retenido: cualquiera que se suscriba después verá el estado actual
        # sin tener que esperar al siguiente mensaje.
        cliente.publish(T_ESTADO, "online", qos=1, retain=True)
        cliente.subscribe(T_COMANDOS, qos=1)
        self.contar(f"MQTT conectado como '{ID}' y suscrito a {T_COMANDOS}", "ok", protocolo="mqtt")

    def _al_recibir(self, cliente, userdata, mensaje: mqtt.MQTTMessage):
        try:
            orden = json.loads(mensaje.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.contar("Comando MQTT ilegible, lo ignoro", "error", protocolo="mqtt")
            return
        if "intervalo_s" in orden:
            self.intervalo_mqtt = float(orden["intervalo_s"])
            self.contar(
                f"Comando recibido por MQTT: intervalo = {self.intervalo_mqtt}s "
                f"(llegó empujado, sin preguntar)",
                "ok",
                protocolo="mqtt",
            )
        if orden.get("cmd_id"):
            cliente.publish(T_ACK, json.dumps({"cmd_id": orden["cmd_id"]}), qos=1)

    def cortar_mqtt(self) -> None:
        """Corta la conexión a lo bestia, SIN enviar DISCONNECT.

        Esto es lo que pasa cuando se va la luz o se cae la red: el broker no
        recibe despedida y publica el testamento.
        """
        if not self.mqtt_vivo:
            return
        self.mqtt_vivo = False
        conector = self.cliente.socket()
        self.cliente.loop_stop()
        try:
            if conector is not None:
                conector.close()
        except OSError:
            pass
        self.contar("Conexión MQTT cortada sin despedida: debería aparecer el testamento",
                    "error", protocolo="mqtt")

    def levantar_mqtt(self) -> None:
        if self.mqtt_vivo:
            return
        try:
            self.cliente.reconnect()
        except OSError:
            try:
                self.cliente.connect(MQTT_HOST, MQTT_PUERTO, keepalive=20)
            except OSError as error:
                self.contar(f"No pude reconectar MQTT: {error}", "error", protocolo="mqtt")
                return
        self.cliente.loop_start()

    # -- HTTP -------------------------------------------------------------

    def enviar_http(self, muestra: dict, max_intentos: int = 3) -> bool:
        """Envía una muestra con reintentos. Esta es la lógica del lab L3."""
        espera = 1.0
        for intento in range(1, max_intentos + 1):
            if self.red_caida:
                return False
            try:
                r = self.sesion.post(
                    f"{API}/telemetry", json=muestra, headers=CABECERAS, timeout=5
                )
            except requests.RequestException as error:
                self.contar(f"HTTP sin respuesta ({error.__class__.__name__}), "
                            f"reintento {intento}", "error", reintento=True)
            else:
                if r.status_code < 300:
                    return True
                if 400 <= r.status_code < 500 and r.status_code != 429:
                    # Es MI error: reintentar igual no lo va a arreglar.
                    self.contar(f"HTTP {r.status_code}: error mío, descarto la muestra",
                                "error")
                    return True
                self.contar(f"HTTP {r.status_code}: reintento {intento} en "
                            f"{espera:.1f}s", "aviso", reintento=True)
            # Backoff exponencial + jitter: si 10.000 dispositivos reintentaran
            # al mismo segundo, tumbarían el servidor otra vez.
            time.sleep(espera + random.uniform(0, 0.4))
            espera = min(espera * 2, 20)
        return False

    def vaciar_cola(self) -> None:
        while self.cola and not self.red_caida:
            muestra = self.cola[0]
            if not self.enviar_http(muestra):
                return
            self.cola.pop(0)
        if not self.cola:
            return

    # -- bucles -----------------------------------------------------------

    def bucle_http(self) -> None:
        while True:
            muestra = self.leer_sensor()
            if self.red_caida:
                if len(self.cola) < 200:
                    self.cola.append(muestra)
                    self.contar(f"Sin red: muestra guardada en la cola local "
                                f"({len(self.cola)} pendientes)", "aviso")
            else:
                if self.cola:
                    pendientes = len(self.cola)
                    self.vaciar_cola()
                    if not self.cola:
                        self.contar(f"Red recuperada: envié las {pendientes} muestras "
                                    f"que tenía en cola, sin perder ninguna", "ok")
                self.enviar_http(muestra)
            time.sleep(self.intervalo_http)

    def bucle_mqtt(self) -> None:
        while True:
            if not self.red_caida and self.mqtt_vivo:
                self.cliente.publish(T_TELEMETRIA, json.dumps(self.leer_sensor()), qos=0)
            time.sleep(self.intervalo_mqtt)

    def bucle_polling(self) -> None:
        """El canal HTTP preguntando si hay novedades. Esto es el *polling*."""
        while True:
            time.sleep(POLL_CONFIG_S)
            if self.red_caida:
                continue
            try:
                r = self.sesion.get(f"{API}/config", timeout=5)
                config = r.json()
            except (requests.RequestException, ValueError):
                continue
            if config.get("version") != self.version_config:
                primera_vez = self.version_config == 0
                self.version_config = config.get("version")
                self.intervalo_http = float(config.get("intervalo_s", 5))
                if primera_vez:
                    continue  # sincronización inicial, no es un comando
                self.contar(
                    f"Configuración nueva detectada por polling: intervalo = "
                    f"{self.intervalo_http}s (tuve que preguntar para enterarme)",
                    "ok",
                )
                if config.get("cmd_id"):
                    try:
                        self.sesion.post(f"{API}/ack",
                                         json={"cmd_id": config["cmd_id"]},
                                         headers=CABECERAS, timeout=5)
                    except requests.RequestException:
                        pass

    def bucle_control(self) -> None:
        """Escucha los interruptores del laboratorio (fuera de banda)."""
        while True:
            try:
                control = self.sesion.get(f"{API}/sim/control", timeout=3).json()
            except (requests.RequestException, ValueError):
                time.sleep(1)
                continue
            caida = bool(control.get("red_caida"))
            if caida != self.red_caida:
                self.red_caida = caida
                if caida:
                    self.cortar_mqtt()
                else:
                    self.levantar_mqtt()
            time.sleep(1)


def esperar_al_servidor(sesion: requests.Session) -> None:
    for _ in range(60):
        try:
            sesion.get(f"{API}/sim/control", timeout=2)
            return
        except requests.RequestException:
            time.sleep(1)


def main() -> None:
    dispositivo = Dispositivo()
    esperar_al_servidor(dispositivo.sesion)

    dispositivo.cliente.connect_async(MQTT_HOST, MQTT_PUERTO, keepalive=20)
    dispositivo.cliente.loop_start()

    for bucle in (dispositivo.bucle_http, dispositivo.bucle_mqtt,
                  dispositivo.bucle_polling, dispositivo.bucle_control):
        threading.Thread(target=bucle, daemon=True).start()

    dispositivo.contar(f"Dispositivo '{ID}' en marcha: HTTP hacia {API} y MQTT "
                       f"hacia {MQTT_HOST}:{MQTT_PUERTO}", "ok")

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
