"""El dispositivo del simulador: el mismo equipo, hablando en local.

QUÉ ES ESTO
    Un tanque con una bomba, igual que el del laboratorio 04. Publica el
    mismo payload, con los mismos nombres de campo:

        {"nivel": 72.4, "temp": 24.1, "alarma": false}

    La única diferencia con shadow_dispositivo.py es con quién habla: aquí
    es un Mosquitto en tu laptop, sin certificados y sin cuenta de AWS. Eso
    permite equivocarse veinte veces en clase sin gastar nada.

    El resto del simulador —las reglas, las funciones— vive en el navegador.
    Este archivo solo produce los datos y obedece.

EL LAZO CERRADO
    Se suscribe a 'simulador/shadow/desired'. Cuando la función Lambda del
    navegador escribe ahí que la bomba debe apagarse, este programa la
    apaga, y el nivel del tanque empieza a bajar en la gráfica. Es el mismo
    ciclo de la clase 4, en pequeño: alguien declara un estado y el equipo
    obedece.
"""

import json
import os
import random
import time

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "localhost")
PUERTO = int(os.getenv("MQTT_PORT", "1883"))
ID = os.getenv("DISPOSITIVO_ID", "tanque-01")
INTERVALO = float(os.getenv("INTERVALO_S", "2"))

TOPIC_TELEMETRIA = f"fablab/planta1/{ID}/telemetria"
TOPIC_DESEADO = "simulador/shadow/desired"
TOPIC_ESTADO = "simulador/estado"
TOPIC_CONTROL = "simulador/control"

# El estado del equipo. Arranca con la bomba encendida a propósito: así el
# nivel sube solo y la alarma salta en menos de un minuto, que es lo que
# necesita una demostración en clase.
estado = {
    "bomba": "encendida",
    "umbral": 90,
}

nivel = 60.0


def publicar_estado(cliente):
    """Le cuenta a la interfaz cómo está el equipo, para dibujarlo."""
    cliente.publish(TOPIC_ESTADO, json.dumps(estado), retain=True)


def al_conectar(cliente, userdata, flags, codigo, propiedades=None):
    print(f"Conectado al broker. Publicando en {TOPIC_TELEMETRIA}", flush=True)
    cliente.subscribe(TOPIC_DESEADO, qos=1)
    cliente.subscribe(TOPIC_CONTROL, qos=1)
    publicar_estado(cliente)


def al_recibir(cliente, userdata, mensaje):
    global nivel

    try:
        cuerpo = json.loads(mensaje.payload.decode() or "{}")
    except json.JSONDecodeError:
        return

    # Una orden de la "Lambda": el estado deseado.
    if mensaje.topic == TOPIC_DESEADO:
        for clave, valor in cuerpo.items():
            if clave in estado:
                print(f"  {clave}: {estado[clave]} -> {valor}", flush=True)
                estado[clave] = valor
        publicar_estado(cliente)

    # El botón de reiniciar de la interfaz: deja todo como al principio para
    # poder repetir la demostración delante de la clase.
    elif mensaje.topic == TOPIC_CONTROL and cuerpo.get("reiniciar"):
        nivel = 60.0
        estado["bomba"] = "encendida"
        estado["umbral"] = 90
        print("Reiniciado", flush=True)
        publicar_estado(cliente)


def medir() -> dict:
    """Una lectura del tanque. El nivel depende de la bomba."""
    global nivel

    if estado["bomba"] == "encendida":
        nivel += random.uniform(2, 6)
    else:
        nivel -= random.uniform(1, 4)

    nivel = max(0.0, min(100.0, nivel))

    return {
        "nivel": round(nivel, 1),
        "temp": round(random.uniform(18, 36), 1),
        # La alarma la decide el equipo, con el umbral que tiene guardado.
        # La nube configura; el dispositivo decide en tiempo real.
        "alarma": nivel > estado["umbral"],
    }


def main() -> None:
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{ID}-sim")
    cliente.on_connect = al_conectar
    cliente.on_message = al_recibir

    # Reintenta hasta que el broker esté listo: en un arranque de Docker el
    # orden no está garantizado y un error aquí deja la clase sin datos.
    while True:
        try:
            cliente.connect(HOST, PUERTO, keepalive=30)
            break
        except OSError:
            print("Esperando al broker...", flush=True)
            time.sleep(2)

    cliente.loop_start()

    try:
        while True:
            muestra = medir()
            cliente.publish(TOPIC_TELEMETRIA, json.dumps(muestra), qos=0)
            print(f"tx {muestra}", flush=True)
            time.sleep(INTERVALO)
    except KeyboardInterrupt:
        pass
    finally:
        cliente.loop_stop()
        cliente.disconnect()


if __name__ == "__main__":
    main()
