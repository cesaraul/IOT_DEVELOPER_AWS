"""Ejemplo mínimo: TRANSMITIR datos por MQTT.

Publica una muestra de sensor cada 5 segundos en tu propio topic.
Déjalo corriendo y mira cómo aparecen los mensajes en la interfaz del
laboratorio (http://localhost:8000), en la pestaña Inspector.

    python publicar.py

Para detenerlo: Ctrl + C
"""

import json
import os
import random
import time

import paho.mqtt.client as mqtt

# Dónde está el broker. "localhost" si lo levantaste con Docker en tu PC.
HOST = os.getenv("MQTT_HOST", "localhost")
PUERTO = int(os.getenv("MQTT_PORT", "1883"))

# Cambia este nombre por el tuyo: dos clientes con el mismo id se expulsan.
ID = os.getenv("DISPOSITIVO_ID", "mi-sensor")

TOPIC = f"fablab/planta1/{ID}/telemetria"


def leer_sensor() -> dict:
    """Aquí leerías tu sensor de verdad. Por ahora, valores inventados."""
    return {
        "temp": round(random.uniform(18, 36), 1),
        "nivel": random.randint(0, 100),
        "ts": round(time.time(), 1),
    }


def main() -> None:
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=ID)
    cliente.connect(HOST, PUERTO, keepalive=30)
    cliente.loop_start()

    print(f"Conectado a {HOST}:{PUERTO}")
    print(f"Publicando en {TOPIC} cada 5 segundos. Ctrl+C para salir.\n")

    try:
        while True:
            muestra = leer_sensor()
            cliente.publish(TOPIC, json.dumps(muestra), qos=0)
            print("enviado:", muestra)
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nHasta luego.")
    finally:
        cliente.loop_stop()
        cliente.disconnect()


if __name__ == "__main__":
    main()
