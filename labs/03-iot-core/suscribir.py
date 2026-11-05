"""Recibir comandos desde AWS IoT Core.

Deja esto corriendo y publica un mensaje desde la consola de AWS
(IoT Core -> Test -> MQTT test client -> "Publish to a topic") en el topic
que aparece abajo. Llega al instante, sin que el dispositivo pregunte nada.

    docker compose run --rm aws python suscribir.py
"""

import os
import ssl

import paho.mqtt.client as mqtt

import config

# Por defecto nos identificamos con el nombre del Thing, porque muchas
# políticas solo permiten conectarse con ese identificador exacto.
# Consecuencia: NO ejecutes publicar.py y suscribir.py a la vez, o se
# expulsan entre ellos. Si tu política lo permite, puedes diferenciarlos:
#   CLIENT_ID=mi-dispositivo-sub docker compose run --rm aws python suscribir.py
CLIENT_ID = os.getenv("CLIENT_ID", config.ID)

rutas = config.identidad()
if not rutas:
    config.abandonar("Faltan los certificados en la carpeta 'certificados'.")
if not config.ENDPOINT:
    config.abandonar("Falta tu endpoint. Revisa el archivo .env.")

CERTIFICADO, LLAVE, RAIZ = rutas


def al_conectar(cliente, userdata, flags, codigo, propiedades=None):
    print(f"Conectado a AWS ({codigo})")
    print(f"Escuchando {config.TOPIC_COMANDOS}. Ctrl+C para salir.\n")
    cliente.subscribe(config.TOPIC_COMANDOS, qos=1)


def al_recibir(cliente, userdata, mensaje):
    print(f"{mensaje.topic}  ->  {mensaje.payload.decode(errors='replace')}")


def main() -> None:
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
    cliente.on_connect = al_conectar
    cliente.on_message = al_recibir

    cliente.tls_set(
        ca_certs=RAIZ,
        certfile=CERTIFICADO,
        keyfile=LLAVE,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )
    cliente.connect(config.ENDPOINT, config.PUERTO, keepalive=30)

    try:
        cliente.loop_forever()
    except KeyboardInterrupt:
        print("\nHasta luego.")
        cliente.disconnect()


if __name__ == "__main__":
    main()
