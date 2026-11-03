"""Estado compartido del laboratorio.

Todo vive en memoria a propósito: reiniciar el contenedor deja el laboratorio
limpio para la siguiente clase. No hay base de datos y no hace falta.
"""

from __future__ import annotations

import threading
import time
import uuid


def _contadores_en_cero() -> dict:
    return {
        "mensajes": 0,
        "bytes_total": 0,     # lo que realmente viaja por la red
        "bytes_utiles": 0,    # solo el dato del sensor
        "errores": 0,
        "reintentos": 0,
        # Solo HTTP: lo que cuesta preguntar "¿hay novedades?" (GET /config).
        "polls": 0,
        "bytes_polling": 0,
    }


class Estado:
    """Un único objeto con todo lo que la interfaz necesita mostrar."""

    def __init__(self) -> None:
        self._cerrojo = threading.Lock()

        # Configuración que el "dispositivo" obtiene por HTTP (GET /config).
        self.config = {"intervalo_s": 5.0, "umbral_temp": 30.0, "version": 1}

        # El canal MQTT lleva su propio intervalo, para que cada protocolo se
        # pueda comandar por separado y la comparación sea limpia.
        self.intervalo_mqtt = 5.0

        # Fallos que el instructor inyecta desde la interfaz.
        self.fallos = {
            "tasa_503": 0.0,      # probabilidad de responder "servidor ocupado"
            "tasa_429": 0.0,      # probabilidad de responder "demasiadas peticiones"
            "latencia_ms": 0,     # retardo artificial del servidor
            "red_caida": False,   # el dispositivo pierde la conexión
        }

        self.metricas = {"http": _contadores_en_cero(), "mqtt": _contadores_en_cero()}
        self.inicio = time.time()

        # Comandos en vuelo, para medir la latencia de extremo a extremo.
        self.comandos: dict[str, dict] = {}

        # Último comando pendiente de que el dispositivo lo recoja por HTTP.
        self.comando_http: str | None = None

        # Topics vistos por el espía, para el explorador de topics.
        self.topics: dict[str, dict] = {}

    # -- métricas ---------------------------------------------------------

    def anotar_mensaje(self, protocolo: str, bytes_total: int, bytes_utiles: int) -> None:
        with self._cerrojo:
            m = self.metricas[protocolo]
            m["mensajes"] += 1
            m["bytes_total"] += bytes_total
            m["bytes_utiles"] += bytes_utiles

    def anotar_polling(self, bytes_total: int) -> None:
        """El polling no lleva datos, pero cuesta. Se cuenta aparte para que la
        comparación de telemetría siga siendo manzanas con manzanas."""
        with self._cerrojo:
            m = self.metricas["http"]
            m["polls"] += 1
            m["bytes_polling"] += bytes_total

    def anotar_error(self, protocolo: str) -> None:
        with self._cerrojo:
            self.metricas[protocolo]["errores"] += 1

    def anotar_reintento(self, protocolo: str) -> None:
        with self._cerrojo:
            self.metricas[protocolo]["reintentos"] += 1

    def reiniciar_metricas(self) -> None:
        with self._cerrojo:
            self.metricas = {"http": _contadores_en_cero(), "mqtt": _contadores_en_cero()}
            self.inicio = time.time()
            self.topics = {}

    def resumen(self) -> dict:
        """Lo que pinta el comparador: incluye la proyección a un mes."""
        with self._cerrojo:
            salida = {}
            for protocolo, m in self.metricas.items():
                eficiencia = (100 * m["bytes_utiles"] / m["bytes_total"]) if m["bytes_total"] else 0.0
                por_mensaje = (m["bytes_total"] / m["mensajes"]) if m["mensajes"] else 0.0
                # 30 días enviando una muestra cada intervalo del propio canal.
                intervalo = self.config["intervalo_s"] if protocolo == "http" else self.intervalo_mqtt
                envios_mes = (30 * 24 * 3600) / max(intervalo, 0.1)
                salida[protocolo] = {
                    **m,
                    "eficiencia": round(eficiencia, 1),
                    "bytes_por_mensaje": round(por_mensaje, 1),
                    "mb_por_mes": round(por_mensaje * envios_mes / 1_000_000, 1),
                }
            return salida

    # -- comandos ---------------------------------------------------------

    def registrar_comando(self, via: str, intervalo: float) -> str:
        cmd_id = uuid.uuid4().hex[:8]
        with self._cerrojo:
            self.comandos[cmd_id] = {"via": via, "intervalo": intervalo, "t0": time.time()}
            if via == "http":
                # El dispositivo se enterará recién en su próximo GET /config.
                self.config["intervalo_s"] = intervalo
                self.config["version"] += 1
                self.comando_http = cmd_id
            else:
                # Por MQTT el broker lo empuja de inmediato.
                self.intervalo_mqtt = intervalo
        return cmd_id

    def cerrar_comando(self, cmd_id: str) -> dict | None:
        """Lo llama el acuse de recibo del dispositivo. Devuelve la latencia."""
        with self._cerrojo:
            comando = self.comandos.pop(cmd_id, None)
            if comando is None:
                return None
            if self.comando_http == cmd_id:
                self.comando_http = None
            return {
                "cmd_id": cmd_id,
                "via": comando["via"],
                "intervalo": comando["intervalo"],
                "latencia_ms": round((time.time() - comando["t0"]) * 1000),
            }

    # -- topics -----------------------------------------------------------

    def anotar_topic(self, topic: str, carga: str) -> None:
        with self._cerrojo:
            entrada = self.topics.setdefault(topic, {"mensajes": 0})
            entrada["mensajes"] += 1
            entrada["ultimo"] = carga[:120]
            entrada["ts"] = time.time()


estado = Estado()
