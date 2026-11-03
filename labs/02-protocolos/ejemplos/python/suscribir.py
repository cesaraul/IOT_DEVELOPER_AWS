"""Ejemplo mínimo: RECIBIR datos por MQTT.

Se suscribe a un topic y muestra todo lo que llegue. Ábrelo en una segunda
terminal, con publicar.py corriendo en la primera, y verás los mensajes
aparecer al instante.

    python suscribir.py

Por defecto escucha TODO lo que pasa por el broker (fablab/#), así que
también verás el dispositivo simulado del laboratorio. Para escuchar solo
lo tuyo:

    TOPIC=fablab/planta1/mi-sensor/telemetria python suscribir.py

Para detenerlo: Ctrl + C
"""

import os

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "localhost")
PUERTO = int(os.getenv("MQTT_PORT", "1883"))

# El filtro de suscripción. Acepta comodines: + es un nivel, # es todo.
FILTRO = os.getenv("TOPIC", "fablab/#")


def al_conectar(cliente, userdata, flags, codigo, propiedades=None):
    print(f"Conectado a {HOST}:{PUERTO} ({codigo})")
    print(f"Escuchando {FILTRO}. Ctrl+C para salir.\n")
    cliente.subscribe(FILTRO, qos=0)


def al_recibir(cliente, userdata, mensaje):
    print(f"{mensaje.topic}  ->  {mensaje.payload.decode(errors='replace')}")


def main() -> None:
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mi-suscriptor")
    cliente.on_connect = al_conectar
    cliente.on_message = al_recibir
    cliente.connect(HOST, PUERTO, keepalive=30)

    try:
        cliente.loop_forever()
    except KeyboardInterrupt:
        print("\nHasta luego.")
        cliente.disconnect()


if __name__ == "__main__":
    main()
