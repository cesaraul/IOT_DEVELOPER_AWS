"""Diagnóstico: ¿está todo listo para hablar con AWS IoT Core?

Revisa, en orden, las seis cosas que pueden fallar, y dice en castellano qué
hacer con cada una. Ejecútalo antes que nada:

    docker compose run --rm aws python comprobar.py

Si todo sale en verde, publicar.py va a funcionar.
"""

import socket
import ssl
import sys
import time

import paho.mqtt.client as mqtt

import config

VERDE = "\033[92m"
ROJO = "\033[91m"
GRIS = "\033[90m"
FIN = "\033[0m"

fallos = 0


def bien(texto: str) -> None:
    print(f"  {VERDE}OK{FIN}    {texto}")


def mal(texto: str, arreglo: str) -> None:
    global fallos
    fallos += 1
    print(f"  {ROJO}FALTA{FIN} {texto}")
    for linea in arreglo.strip().splitlines():
        print(f"        {GRIS}{linea.strip()}{FIN}")


def titulo(texto: str) -> None:
    print(f"\n{texto}")
    print("-" * 66)


# --- 1. Los archivos del certificado -------------------------------------

titulo("1. Los archivos de tu dispositivo")

cert, llave, raiz = config.certificado(), config.llave_privada(), config.raiz_amazon()

if cert:
    bien(f"certificado del dispositivo: {cert.split('/')[-1]}")
else:
    mal(
        "no encuentro el certificado del dispositivo",
        """Debe ser el archivo que termina en -certificate.pem.crt
           Descomprime el connection kit dentro de la carpeta 'certificados'
           que está junto a este laboratorio.""",
    )

if llave:
    bien(f"llave privada: {llave.split('/')[-1]}")
else:
    mal(
        "no encuentro la llave privada",
        """Debe ser el archivo que termina en -private.pem.key
           Ojo: la llave privada solo se puede descargar UNA vez. Si no la
           tienes, crea un certificado nuevo y adjúntalo al mismo Thing.""",
    )

if raiz:
    bien(f"certificado raíz de Amazon: {raiz.split('/')[-1]}")
else:
    mal(
        "no encuentro AmazonRootCA1.pem",
        """Viene dentro del connection kit. Si no está, descárgalo de
           https://www.amazontrust.com/repository/AmazonRootCA1.pem
           y guárdalo en la carpeta 'certificados'.""",
    )

# --- 2. El endpoint -------------------------------------------------------

titulo("2. La dirección de tu cuenta (endpoint)")

if not config.ENDPOINT:
    mal(
        "no has puesto tu endpoint",
        """Copia .env.example como .env y escribe ahí AWS_IOT_ENDPOINT.
           Lo encuentras en la consola: IoT Core -> Settings ->
           "Device data endpoint".""",
    )
elif not config.ENDPOINT.endswith("amazonaws.com"):
    mal(
        f"el endpoint no parece correcto: {config.ENDPOINT}",
        """Debe terminar en amazonaws.com y verse así:
           a1b2c3d4e5f6g7-ats.iot.us-east-1.amazonaws.com
           Sin https:// delante y sin barras.""",
    )
else:
    bien(f"endpoint: {config.ENDPOINT}")
    if "-ats." not in config.ENDPOINT:
        print(f"        {GRIS}aviso: normalmente el endpoint lleva '-ats.'{FIN}")

# --- 3. Resolución de nombre ---------------------------------------------

resuelve = False

if config.ENDPOINT:
    titulo("3. ¿Existe esa dirección?")
    try:
        ip = socket.gethostbyname(config.ENDPOINT)
        resuelve = True
        bien(f"el nombre resuelve a {ip}")
    except socket.gaierror:
        mal(
            "esa dirección no existe",
            """Revisa que copiaste el endpoint completo y sin espacios.
               Cada cuenta de AWS tiene el suyo: el de un compañero no sirve.""",
        )

# --- 4. El puerto 8883 ----------------------------------------------------

# Solo tiene sentido si el nombre existe: si no, el fallo sería del endpoint,
# no de la red, y mandaríamos al alumno a revisar el cortafuegos sin motivo.
if config.ENDPOINT and resuelve:
    titulo("4. ¿Deja pasar tu red el puerto 8883?")
    conector = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conector.settimeout(8)
    try:
        conector.connect((config.ENDPOINT, config.PUERTO))
        bien("el puerto 8883 está abierto")
    except (socket.timeout, OSError):
        mal(
            "no se puede abrir el puerto 8883",
            """Tu red lo está bloqueando. Es típico en redes de empresa o de
               universidad. Prueba con otra red (el teléfono compartiendo
               datos sirve) y avísale al instructor.""",
        )
    finally:
        conector.close()

# --- 5. El saludo TLS y la conexión MQTT ---------------------------------

if config.ENDPOINT and cert and llave and raiz and fallos == 0:
    titulo("5. ¿Te reconoce AWS?")

    resultado = {"codigo": None, "cerrada": False}

    def al_conectar(cliente, userdata, flags, codigo, propiedades=None):
        resultado["codigo"] = codigo

    def al_desconectar(cliente, userdata, flags, codigo, propiedades=None):
        # AWS no dice "permiso denegado": simplemente cierra la conexión.
        resultado["cerrada"] = True

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.ID)
    cliente.on_connect = al_conectar
    cliente.on_disconnect = al_desconectar

    try:
        cliente.tls_set(
            ca_certs=raiz,
            certfile=cert,
            keyfile=llave,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
        cliente.connect(config.ENDPOINT, config.PUERTO, keepalive=30)
        cliente.loop_start()

        for _ in range(100):
            if resultado["codigo"] is not None:
                break
            time.sleep(0.1)

        if resultado["codigo"] is None:
            mal(
                "AWS aceptó el cifrado pero cortó la conexión sin responder",
                f"""Esto es casi siempre LA POLÍTICA. AWS nunca dice "permiso
                   denegado": simplemente cuelga.
                   La política que crea el asistente solo deja conectarse con
                   los client-id de su propio ejemplo, no con '{config.ID}'.
                   Arréglalo así: consola -> Security -> Policies -> tu
                   política -> Edit, y pega el contenido de politica-curso.json
                   que está en esta carpeta (cambiando REGION y CUENTA).""",
            )
        elif str(resultado["codigo"]) in ("Success", "0"):
            bien(f"conectado como '{config.ID}'")

            # --- 6. Publicar de verdad ---------------------------------
            titulo("6. ¿Te deja publicar la política?")
            info = cliente.publish(
                config.TOPIC_TELEMETRIA, '{"prueba":true}', qos=1
            )
            info.wait_for_publish(timeout=8)
            if info.is_published():
                bien(f"mensaje de prueba publicado en {config.TOPIC_TELEMETRIA}")
            else:
                mal(
                    "la conexión funciona, pero no te deja publicar",
                    f"""Tu política no permite iot:Publish en ese topic.
                       Consola -> Security -> Policies -> tu política.
                       Topic: {config.TOPIC_TELEMETRIA}""",
                )
        else:
            mal(
                f"AWS rechazó la conexión ({resultado['codigo']})",
                """Casi siempre es la política, o que el certificado no está
                   adjunto al Thing, o que está desactivado.
                   Consola -> Security -> Certificates -> tu certificado:
                   debe estar "Active" y tener política y Thing adjuntos.""",
            )
    except ssl.SSLError as error:
        mal(
            f"falló el cifrado TLS ({error.__class__.__name__})",
            """Revisa que el certificado y la llave sean del MISMO par y que
               AmazonRootCA1.pem no esté corrupto.""",
        )
    except OSError as error:
        mal(f"no se pudo conectar ({error})", "Revisa tu conexión a internet.")
    finally:
        cliente.loop_stop()
        cliente.disconnect()

# --- Resumen --------------------------------------------------------------

print()
if fallos == 0:
    print(f"  {VERDE}Todo listo.{FIN} Ya puedes ejecutar:\n")
    print("      docker compose run --rm aws python publicar.py\n")
    sys.exit(0)

print(f"  {ROJO}Hay {fallos} cosa(s) por arreglar.{FIN} Corrige y vuelve a ejecutar esto.\n")
sys.exit(1)
