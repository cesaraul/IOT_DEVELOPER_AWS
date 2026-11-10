"""Publicar telemetría en AWS IoT Core.

QUÉ HACE
    Lee un "sensor" (de momento, valores inventados) y publica una muestra
    cada 5 segundos en tu propio topic de AWS. Lo ves llegar en la consola:
    IoT Core -> Probar -> Cliente de prueba de MQTT, suscrito a  fablab/#

CÓMO SE EJECUTA
    docker compose run --rm aws python publicar.py

    Para detenerlo: Ctrl + C

LO IMPORTANTE DE ESTE ARCHIVO
    Compáralo con el publicar.py de la clase 2, el que hablaba con el broker
    de tu laptop. Es el MISMO programa. Solo cambian las tres líneas marcadas
    con «NUEVO». El publish, el topic y el payload son idénticos: a tu código
    no le importa si al otro lado hay un Mosquitto en tu máquina o la
    infraestructura de Amazon. Eso es lo que significa que MQTT sea un
    estándar.
"""

# json  -> para convertir el diccionario de Python en el texto que viaja
# random, time -> para inventar lecturas y esperar entre envío y envío
# ssl   -> para decirle a paho qué versión de TLS queremos
import json
import random
import ssl
import time

# La librería cliente de MQTT. Es la misma de la clase 2: no cambia por
# hablar con AWS.
import paho.mqtt.client as mqtt

# Nuestro módulo de configuración: encuentra tus certificados y lee el .env.
import config

# ---------------------------------------------------------------------------
# Antes de nada: ¿tenemos lo necesario para conectarnos?
# ---------------------------------------------------------------------------
# identidad() devuelve las rutas de los tres archivos (certificado, llave
# privada y certificado raíz) o None si falta alguno. Preferimos avisar con
# un mensaje claro antes que reventar con un error de Python a mitad.

rutas = config.identidad()
if not rutas:
    config.abandonar("Faltan los certificados en la carpeta 'certificados'.")
if not config.ENDPOINT:
    config.abandonar("Falta tu endpoint. Revisa el archivo .env.")

CERTIFICADO, LLAVE, RAIZ = rutas


def leer_sensor() -> dict:
    """Devuelve una lectura del sensor.

    Aquí es donde leerías tu hardware de verdad: un sensor de temperatura,
    un medidor de nivel, lo que sea. Mientras tanto, valores inventados con
    un rango creíble.

    El campo 'ts' (timestamp) lo pone el DISPOSITIVO, no la nube. Es una
    buena costumbre: si el mensaje se retrasa o se reenvía, sigues sabiendo
    cuándo se tomó la medición de verdad.
    """
    return {
        "temp": round(random.uniform(18, 36), 1),
        "nivel": random.randint(0, 100),
        "ts": round(time.time(), 1),
    }


def main() -> None:
    # Creamos el cliente. El client_id debe ser ÚNICO en todo el broker: si
    # dos clientes se conectan con el mismo, AWS expulsa a uno de los dos y
    # entran en un bucle de reconexiones muy difícil de diagnosticar.
    # Además, nuestra política solo autoriza a conectarse con el nombre del
    # objeto, así que aquí va exactamente ese nombre.
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.ID)

    # --- NUEVO (1) ----------------------------------------------------------
    # El cifrado y la identidad. Esto es todo lo que AWS añade al código de la
    # clase 2, y hace dos cosas a la vez:
    #
    #   ca_certs  el certificado raíz de Amazon. Con él comprobamos que el
    #             servidor del otro lado es de verdad AWS y no un impostor.
    #   certfile  NUESTRO certificado: lo que demuestra quiénes somos.
    #   keyfile   nuestra llave privada. No sale nunca de este equipo; se usa
    #             para firmar, nunca se envía.
    #
    # A esto se le llama TLS mutuo: en una web normal solo el servidor
    # demuestra quién es; aquí también lo hace el dispositivo.
    cliente.tls_set(
        ca_certs=RAIZ,
        certfile=CERTIFICADO,
        keyfile=LLAVE,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )

    # --- NUEVO (2) y (3) ----------------------------------------------------
    # (2) El endpoint de TU cuenta en vez de "localhost".
    # (3) El puerto 8883 en vez del 1883: en AWS no existe el puerto sin
    #     cifrar. El keepalive son los segundos que el broker espera noticias
    #     tuyas antes de darte por muerto.
    cliente.connect(config.ENDPOINT, config.PUERTO, keepalive=30)

    # loop_start() arranca un hilo en segundo plano que se encarga de la red:
    # mantiene viva la conexión, responde a los pings y reconecta si se cae.
    # Sin él, el programa publicaría a ciegas.
    cliente.loop_start()

    print(f"Conectado a {config.ENDPOINT}")
    print(f"Publicando en {config.TOPIC_TELEMETRIA} cada 5 segundos.")
    print("Míralo llegar en la consola: IoT Core -> Test -> MQTT test client,")
    print("suscrito a  fablab/#\n")

    try:
        while True:
            muestra = leer_sensor()

            # json.dumps convierte el diccionario en texto. El payload de MQTT
            # es binario: puede ser JSON, pero también CBOR o Protobuf si
            # necesitas apretar más los bytes.
            #
            # qos=1 significa "al menos una vez": AWS confirma la recepción.
            # Para telemetría muy frecuente se suele usar qos=0, que no
            # confirma nada y es más barato; aquí usamos 1 porque son pocos
            # mensajes y preferimos verlos llegar todos.
            cliente.publish(config.TOPIC_TELEMETRIA, json.dumps(muestra), qos=1)

            print("enviado:", muestra)
            time.sleep(5)

    except KeyboardInterrupt:
        # Ctrl + C. Salimos de forma ordenada en vez de con un error.
        print("\nHasta luego.")

    finally:
        # Siempre, pase lo que pase: paramos el hilo de red y nos despedimos
        # del broker. Un disconnect() limpio le dice a AWS que nos vamos por
        # las buenas; si el programa muriera de golpe, el broker tardaría
        # hasta 1,5 veces el keepalive en darse cuenta.
        cliente.loop_stop()
        cliente.disconnect()


# Este "if" hace que el código solo se ejecute cuando lanzas el archivo
# directamente, y no cuando otro programa lo importa. Es la costumbre en
# Python y conviene cogerla desde el principio.
if __name__ == "__main__":
    main()
