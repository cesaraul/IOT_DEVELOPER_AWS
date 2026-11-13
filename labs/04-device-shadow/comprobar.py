"""Diagnóstico del laboratorio 04: ¿están listas las DOS identidades?

CÓMO SE EJECUTA
    docker compose run --rm dispositivo python comprobar.py

QUÉ COMPRUEBA, Y POR QUÉ EN ESE ORDEN
    Este laboratorio tiene dos actores que entran a AWS por puertas
    distintas, así que el diagnóstico va en dos mitades:

    EL DISPOSITIVO (certificado X.509, MQTT)
      1. Los tres archivos están, y son del objeto que dice tu .env
      2. El endpoint, y la región que sale de él
      3. La red deja salir por el puerto 8883
      4. AWS te reconoce
      5. Tu política autoriza los topics del shadow   <- lo nuevo de hoy

    LA APLICACIÓN (claves de IAM, API HTTPS)
      6. Las claves están puestas
      7. AWS las acepta y te deja leer el shadow

    Si falla la primera mitad, la segunda no se ejecuta: no tiene sentido
    revisar los permisos de la aplicación si el dispositivo todavía no
    puede conectarse.
"""

import json
import os
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


print()
print("=" * 66)
print("  EL DISPOSITIVO  —  entra con su certificado, por MQTT")
print("=" * 66)

# --- 1. Los archivos ------------------------------------------------------

titulo("1. Los archivos de tu dispositivo")

cert, llave, raiz = config.certificado(), config.llave_privada(), config.raiz_amazon()

if cert:
    bien(f"certificado: {os.path.basename(cert)}")
else:
    mal(
        "no encuentro el certificado del dispositivo",
        """Este laboratorio reutiliza los certificados del 03: no hay que
           descargar nada nuevo. Comprueba que siguen en
           labs/03-iot-core/certificados/.""",
    )

if llave:
    bien(f"llave privada: {os.path.basename(llave)}")
else:
    mal(
        "no encuentro la llave privada",
        """Debe terminar en -private.pem.key, en la misma carpeta del
           laboratorio 03.""",
    )

if raiz:
    bien(f"raíz de Amazon: {os.path.basename(raiz)}")
else:
    mal("no encuentro AmazonRootCA1.pem", "Debería venir incluido en esta carpeta.")

# El cruce que más tiempo hace perder: certificado de un objeto, nombre de otro.
if cert:
    duenio = os.path.basename(cert).split(".")[0].replace("-certificate", "")
    if not os.path.basename(cert).startswith(config.ID):
        mal(
            f"el certificado es de '{duenio}', pero DISPOSITIVO_ID dice '{config.ID}'",
            f"""Presentarias el certificado de un objeto anunciandote como
               otro, y AWS corta la conexion sin avisar. Pon
               DISPOSITIVO_ID={duenio} en el .env del laboratorio 03, o
               descomprime ahi el kit de '{config.ID}'.""",
        )

# --- 2. Endpoint y región -------------------------------------------------

titulo("2. Tu cuenta: endpoint y región")

if not config.ENDPOINT:
    mal(
        "no has puesto tu endpoint",
        """Este laboratorio lee el .env del 03. Comprueba que existe
           labs/03-iot-core/.env y que tiene AWS_IOT_ENDPOINT.""",
    )
elif not config.ENDPOINT.endswith("amazonaws.com"):
    mal(
        f"el endpoint no parece correcto: {config.ENDPOINT}",
        """Debe verse así, sin https:// y sin barras:
           a1b2c3d4e5f6g7-ats.iot.us-east-1.amazonaws.com""",
    )
else:
    bien(f"endpoint: {config.ENDPOINT}")

    if config.region():
        bien(f"región deducida del endpoint: {config.region()}")
    else:
        mal(
            "no pude deducir la región del endpoint",
            """La región va dentro del endpoint, entre 'iot.' y
               '.amazonaws.com'. Si no está, el endpoint está incompleto.""",
        )

# --- 3. El puerto ---------------------------------------------------------

resuelve = False

if config.ENDPOINT:
    titulo("3. ¿Tu red deja salir por el puerto 8883?")
    try:
        socket.gethostbyname(config.ENDPOINT)
        resuelve = True
    except socket.gaierror:
        mal(
            "esa dirección no existe",
            "Revisa que copiaste el endpoint completo y sin espacios.",
        )

    if resuelve:
        conector = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conector.settimeout(8)
        try:
            conector.connect((config.ENDPOINT, config.PUERTO))
            bien("el puerto 8883 está abierto")
        except (socket.timeout, OSError):
            mal(
                "no se puede abrir el puerto 8883",
                """Tu red lo bloquea. Prueba compartiendo datos del teléfono.""",
            )
        finally:
            conector.close()

# --- 4 y 5. Conexión y permisos de shadow ---------------------------------

if cert and llave and raiz and config.ENDPOINT and fallos == 0:
    titulo("4. ¿Te reconoce AWS?")

    visto = {"conectado": False, "respuesta": None, "suscrito": False}

    def al_conectar(cliente, userdata, flags, codigo, propiedades=None):
        visto["conectado"] = str(codigo) in ("Success", "0")

    def al_suscribir(cliente, userdata, mid, codigos, propiedades=None):
        visto["suscrito"] = True

    def al_recibir(cliente, userdata, mensaje):
        visto["respuesta"] = mensaje.topic

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.ID)
    cliente.on_connect = al_conectar
    cliente.on_subscribe = al_suscribir
    cliente.on_message = al_recibir

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
            if visto["conectado"]:
                break
            time.sleep(0.1)

        if not visto["conectado"]:
            mal(
                "AWS aceptó el cifrado pero cortó la conexión",
                """Casi siempre es la política, igual que en el laboratorio 03.
                   Genera la tuya con:
                   docker compose run --rm dispositivo python generar_politica.py""",
            )
        else:
            bien(f"conectado como '{config.ID}'")

            # --- 5. Los permisos del shadow ---------------------------
            titulo("5. ¿Tu política autoriza el shadow?")

            # La prueba real: suscribirse a las respuestas y pedir el
            # documento. Si la política no cubre los topics $aws/..., AWS
            # corta la conexión en cuanto intentamos suscribirnos. No hay
            # mensaje de error: hay silencio y desconexión.
            cliente.subscribe(config.TOPIC_GET_ACEPTADO, qos=1)
            cliente.subscribe(config.TOPIC_GET_RECHAZADO, qos=1)
            time.sleep(1.5)
            cliente.publish(config.TOPIC_GET, "", qos=1)

            for _ in range(80):
                if visto["respuesta"]:
                    break
                time.sleep(0.1)

            if visto["respuesta"] == config.TOPIC_GET_ACEPTADO:
                bien("puedes leer tu shadow (y ya tiene contenido)")
            elif visto["respuesta"] == config.TOPIC_GET_RECHAZADO:
                bien("puedes hablar con el shadow (todavía no existe: normal)")
                print(f"        {GRIS}se creará al arrancar shadow_dispositivo.py{FIN}")
            else:
                mal(
                    "tu política NO autoriza los topics del shadow",
                    """Es lo esperado la primera vez: la política del
                       laboratorio 03 solo cubre fablab/planta1/*, y los
                       topics del shadow empiezan por $aws/things/...
                       Genera la política nueva:
                       docker compose run --rm dispositivo python generar_politica.py
                       y pégala en Security -> Policies -> tu política -> Edit,
                       marcando «establecer como versión activa».""",
                )

    except ssl.SSLError as error:
        mal(
            f"falló el cifrado TLS ({error.__class__.__name__})",
            "Revisa que el certificado y la llave sean del MISMO par.",
        )
    except OSError as error:
        mal(f"no se pudo conectar ({error})", "Revisa tu conexión a internet.")
    finally:
        cliente.loop_stop()
        cliente.disconnect()

# --- 6 y 7. La aplicación -------------------------------------------------

if fallos == 0:
    print()
    print("=" * 66)
    print("  LA APLICACIÓN  —  entra con claves de IAM, por HTTPS")
    print("=" * 66)

    titulo("6. ¿Están las claves del usuario de IAM?")

    if not config.CLAVE_ID or not config.CLAVE_SECRETA:
        mal(
            "faltan AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY",
            """Van en el archivo .env de ESTA carpeta (no el del 03).
               Se crean en: IAM -> Usuarios -> tu usuario ->
               Credenciales de seguridad -> Crear clave de acceso.
               Ojo: la clave secreta se muestra UNA sola vez.""",
        )
    else:
        bien(f"clave de acceso: {config.CLAVE_ID[:4]}...{config.CLAVE_ID[-4:]}")

        titulo("7. ¿AWS acepta esas claves para leer el shadow?")
        try:
            import boto3
            from botocore.exceptions import ClientError

            iot = boto3.client(
                "iot-data",
                region_name=config.region(),
                endpoint_url=f"https://{config.ENDPOINT}",
            )
            respuesta = iot.get_thing_shadow(thingName=config.ID)
            json.loads(respuesta["payload"].read())
            bien("la aplicación puede leer el shadow")

        except ClientError as error:
            codigo = error.response["Error"]["Code"]

            if codigo == "ResourceNotFoundException":
                bien("las claves funcionan (el shadow aún no existe: normal)")
                print(f"        {GRIS}arranca shadow_dispositivo.py y se creará{FIN}")

            elif codigo in ("AccessDeniedException", "ForbiddenException"):
                mal(
                    "las claves son válidas, pero el usuario no tiene permiso",
                    """Le faltan iot:GetThingShadow e iot:UpdateThingShadow.
                       Genera su política:
                       docker compose run --rm dispositivo python generar_politica.py
                       y pégala en IAM -> Usuarios -> tu usuario -> Permisos.""",
                )

            elif codigo in ("UnrecognizedClientException", "InvalidSignatureException"):
                mal(
                    "AWS no reconoce esas claves",
                    """Suele ser un copiar-pegar incompleto o una clave
                       borrada. Crea una nueva y ponla en el .env.""",
                )

            else:
                mal(f"AWS devolvió {codigo}", error.response["Error"]["Message"])

# --- Resumen --------------------------------------------------------------

print()
if fallos == 0:
    print(f"  {VERDE}Las dos identidades funcionan.{FIN} Abre dos terminales:\n")
    print("      docker compose run --rm dispositivo python shadow_dispositivo.py")
    print("      docker compose run --rm app python shadow_app.py encender\n")
    sys.exit(0)

print(f"  {ROJO}Hay {fallos} cosa(s) por arreglar.{FIN} Corrige y vuelve a ejecutar.\n")
sys.exit(1)
