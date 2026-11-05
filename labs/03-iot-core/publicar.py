"""Publicar telemetría en AWS IoT Core.

Compáralo con el publicar.py de la clase 2: es el MISMO programa. Lo único
que cambia son las tres líneas marcadas con «NUEVO».

    docker compose run --rm aws python publicar.py
"""

import json
import random
import ssl
import time

import paho.mqtt.client as mqtt

import config

rutas = config.identidad()
if not rutas:
    config.abandonar("Faltan los certificados en la carpeta 'certificados'.")
if not config.ENDPOINT:
    config.abandonar("Falta tu endpoint. Revisa el archivo .env.")

CERTIFICADO, LLAVE, RAIZ = rutas


def leer_sensor() -> dict:
    """Aquí leerías tu sensor de verdad. Por ahora, valores inventados."""
    return {
        "temp": round(random.uniform(18, 36), 1),
        "nivel": random.randint(0, 100),
        "ts": round(time.time(), 1),
    }


def main() -> None:
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.ID)

    # NUEVO (1): el cifrado y la identidad. Esto es todo lo que AWS añade.
    #   - ca_certs : con qué comprobamos que el servidor es de verdad Amazon
    #   - certfile : nuestro certificado, lo que demuestra quiénes somos
    #   - keyfile  : nuestra llave privada, que nunca sale de aquí
    cliente.tls_set(
        ca_certs=RAIZ,
        certfile=CERTIFICADO,
        keyfile=LLAVE,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )

    # NUEVO (2): el endpoint de tu cuenta en vez de "localhost".
    # NUEVO (3): el puerto 8883 en vez del 1883. En AWS no hay puerto sin cifrar.
    cliente.connect(config.ENDPOINT, config.PUERTO, keepalive=30)
    cliente.loop_start()

    print(f"Conectado a {config.ENDPOINT}")
    print(f"Publicando en {config.TOPIC_TELEMETRIA} cada 5 segundos.")
    print("Míralo llegar en la consola: IoT Core -> Test -> MQTT test client,")
    print("suscrito a  fablab/#\n")

    try:
        while True:
            muestra = leer_sensor()
            cliente.publish(config.TOPIC_TELEMETRIA, json.dumps(muestra), qos=1)
            print("enviado:", muestra)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nHasta luego.")
    finally:
        cliente.loop_stop()
        cliente.disconnect()


if __name__ == "__main__":
    main()
