"""Recibir comandos desde AWS IoT Core.

QUÉ HACE
    Se queda escuchando tu topic de comandos. Cuando alguien publica algo
    ahí, el broker te lo EMPUJA al instante: tu programa no pregunta nada.

CÓMO SE EJECUTA
    docker compose run --rm aws python suscribir.py

    Y entonces, desde la consola de AWS:
        IoT Core -> Probar -> Cliente de prueba de MQTT
        pestaña "Publicar en un tema"
        tema:    fablab/planta1/TU-ID/comandos
        mensaje: lo que quieras

    Para detenerlo: Ctrl + C

LO IMPORTANTE DE ESTE ARCHIVO
    Esto es el "push" del que hablamos en la clase 2, ahora contra AWS. Con
    HTTP tendrías que preguntar cada pocos segundos a ver si hay novedades;
    aquí la conexión ya está abierta y el mensaje llega solo.
"""

import os
import ssl

import paho.mqtt.client as mqtt

import config

# ---------------------------------------------------------------------------
# Con qué nombre nos identificamos
# ---------------------------------------------------------------------------
# Por defecto usamos el nombre del objeto, porque la política del curso solo
# autoriza a conectarse con ese identificador exacto:
#
#     "Resource": "...:client/${iot:Connection.Thing.ThingName}"
#
# Consecuencia práctica: NO ejecutes publicar.py y suscribir.py a la vez, o
# se expulsan mutuamente del broker. Si amplías la política para permitir
# otros nombres, puedes diferenciarlos así:
#
#     CLIENT_ID=mi-dispositivo-sub docker compose run --rm aws python suscribir.py
CLIENT_ID = os.getenv("CLIENT_ID", config.ID)

# Las mismas comprobaciones previas que en publicar.py: mejor un mensaje
# claro que un error de Python a mitad de la conexión.
rutas = config.identidad()
if not rutas:
    config.abandonar("Faltan los certificados en la carpeta 'certificados'.")
if not config.ENDPOINT:
    config.abandonar("Falta tu endpoint. Revisa el archivo .env.")

CERTIFICADO, LLAVE, RAIZ = rutas


def al_conectar(cliente, userdata, flags, codigo, propiedades=None):
    """Se ejecuta cuando el broker acepta la conexión.

    La suscripción va AQUÍ y no antes, por un motivo: si la conexión se cae y
    paho reconecta solo, esta función se vuelve a ejecutar y la suscripción se
    restablece sola. Si la pusiéramos fuera, tras una reconexión estaríamos
    conectados pero sordos.
    """
    print(f"Conectado a AWS ({codigo})")
    print(f"Escuchando {config.TOPIC_COMANDOS}. Ctrl+C para salir.\n")

    # qos=1: pedimos que el broker nos entregue cada mensaje al menos una vez.
    cliente.subscribe(config.TOPIC_COMANDOS, qos=1)


def al_recibir(cliente, userdata, mensaje):
    """Se ejecuta por cada mensaje que llega. Aquí actuarías sobre el equipo.

    mensaje.topic   el tema exacto en el que se publicó
    mensaje.payload el contenido, en bytes (MQTT no sabe de texto)
    mensaje.qos     la calidad de servicio con la que llegó
    """
    # decode() convierte los bytes en texto. errors="replace" evita que el
    # programa se caiga si alguien publica algo que no es texto válido: un
    # dispositivo en campo no se puede permitir morir por un mensaje raro.
    print(f"{mensaje.topic}  ->  {mensaje.payload.decode(errors='replace')}")


def main() -> None:
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)

    # Registramos las dos funciones de arriba. paho las llamará solo, cuando
    # toque: no hay que estar preguntando en un bucle.
    cliente.on_connect = al_conectar
    cliente.on_message = al_recibir

    # El cifrado y la identidad, igual que en publicar.py.
    cliente.tls_set(
        ca_certs=RAIZ,
        certfile=CERTIFICADO,
        keyfile=LLAVE,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )
    cliente.connect(config.ENDPOINT, config.PUERTO, keepalive=30)

    try:
        # loop_forever() se queda aquí dentro para siempre, atendiendo la red
        # y llamando a al_recibir cuando llega algo. Es la diferencia con
        # publicar.py, que usaba loop_start() porque además tenía que seguir
        # con su propio bucle de envíos.
        cliente.loop_forever()
    except KeyboardInterrupt:
        print("\nHasta luego.")
        cliente.disconnect()


if __name__ == "__main__":
    main()
