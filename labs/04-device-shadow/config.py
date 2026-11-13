"""Configuración compartida del laboratorio 04.

QUÉ TRAE DE NUEVO RESPECTO AL LABORATORIO 03
    1. Los topics del shadow, que no los inventamos nosotros: los define AWS
       y empiezan por $aws. Están todos armados aquí abajo para que no haya
       que escribirlos a mano (y escribirlos a mano es la primera causa de
       que un laboratorio de shadow no funcione).
    2. La región, deducida del endpoint. El SDK la necesita y ya la tienes
       escrita dentro de la dirección de tu cuenta, así que no te la vamos a
       volver a pedir.
    3. Las claves del usuario de IAM, que usa la APLICACIÓN. El dispositivo
       sigue usando su certificado: son dos identidades distintas y conviene
       verlas separadas también en el código.

    No necesitas tocar nada de aquí. Lo que se configura va en los .env.
"""

from __future__ import annotations

import glob
import os

# ---------------------------------------------------------------------------
# Lo que viene de fuera
# ---------------------------------------------------------------------------
# Del .env del laboratorio 03 (endpoint y nombre del objeto): no lo repetimos
# aquí para que no haya dos copias que puedan discrepar.
CARPETA = os.getenv("CARPETA_CERTIFICADOS", "/certificados")
ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "").strip()
ID = os.getenv("DISPOSITIVO_ID", "mi-dispositivo").strip()

# Del .env de este laboratorio: las claves del usuario de IAM. Las lee boto3
# solo, por su nombre estándar; las repetimos aquí únicamente para poder
# avisar con un mensaje claro cuando falten.
CLAVE_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
CLAVE_SECRETA = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

PUERTO = 8883


def region() -> str:
    """Saca la región de dentro del endpoint.

    El endpoint tiene esta forma, y la región es el penúltimo trozo:

        a1b2c3d4e5f6g7-ats.iot.us-east-2.amazonaws.com
                            └── esto ──┘

    Lo hacemos así, y no pidiéndola en el .env, porque un dato escrito dos
    veces es un dato que algún día va a discrepar consigo mismo.
    """
    partes = ENDPOINT.split(".")
    # ['a1b2...-ats', 'iot', 'us-east-2', 'amazonaws', 'com']
    if len(partes) >= 4 and partes[1] == "iot":
        return partes[2]
    return ""


# ---------------------------------------------------------------------------
# Los topics del shadow
# ---------------------------------------------------------------------------
# Estos NO los eliges tú. Son topics reservados: AWS los tiene preparados para
# cada objeto y les da un significado fijo. Por eso empiezan por $aws, que es
# un prefijo que no puedes usar para tus propios topics.
#
# Fíjate en el patrón, porque se repite en todos los servicios de IoT Core:
#   .../algo            -> tú pides
#   .../algo/accepted   -> AWS dice que salió bien
#   .../algo/rejected   -> AWS dice que salió mal, y explica por qué
#
# Y uno que no sigue ese patrón porque no es una respuesta tuya, sino un aviso
# de AWS: /update/delta, que llega cuando hay algo que el dispositivo todavía
# no ha hecho.

SHADOW = f"$aws/things/{ID}/shadow"

TOPIC_UPDATE = f"{SHADOW}/update"
TOPIC_UPDATE_ACEPTADO = f"{SHADOW}/update/accepted"
TOPIC_UPDATE_RECHAZADO = f"{SHADOW}/update/rejected"
TOPIC_DELTA = f"{SHADOW}/update/delta"

TOPIC_GET = f"{SHADOW}/get"
TOPIC_GET_ACEPTADO = f"{SHADOW}/get/accepted"
TOPIC_GET_RECHAZADO = f"{SHADOW}/get/rejected"

# Nos suscribimos a estos cinco, uno por uno. AWS recomienda NO usar comodines
# ($aws/things/X/shadow/#) porque se reserva el derecho de añadir topics
# nuevos a esa estructura: el día que lo haga, tu dispositivo recibiría
# mensajes que no sabe interpretar.
TOPICS_DE_RESPUESTA = [
    TOPIC_UPDATE_ACEPTADO,
    TOPIC_UPDATE_RECHAZADO,
    TOPIC_DELTA,
    TOPIC_GET_ACEPTADO,
    TOPIC_GET_RECHAZADO,
]


# ---------------------------------------------------------------------------
# Localizar los archivos del certificado (igual que en el laboratorio 03)
# ---------------------------------------------------------------------------


def _buscar(patrones: list[str], excluir: str | None = None) -> str | None:
    """Devuelve el archivo de la carpeta que encaje con algún patrón.

    Si tienes kits de varios dispositivos en la misma carpeta, gana el que
    lleva el nombre del que estás usando (DISPOSITIVO_ID).
    """
    for patron in patrones:
        encontrados = sorted(glob.glob(os.path.join(CARPETA, patron)))

        if excluir:
            encontrados = [
                r for r in encontrados if excluir not in os.path.basename(r).lower()
            ]

        if not encontrados:
            continue

        propios = [r for r in encontrados if os.path.basename(r).startswith(ID)]
        return (propios or encontrados)[0]

    return None


def certificado() -> str | None:
    """Tu certificado: el archivo que dice quién eres."""
    return _buscar(["*certificate.pem.crt", "*-certificate.pem", "*.cert.pem", "*.crt"])


def llave_privada() -> str | None:
    """Tu llave privada. La mitad secreta: no sale nunca de este equipo."""
    return _buscar(
        ["*private.pem.key", "*-private.pem", "*.private.key", "*.key"],
        excluir="public",
    )


def raiz_amazon() -> str | None:
    """El certificado raíz de Amazon, para comprobar que el servidor es AWS."""
    propia = _buscar(["*AmazonRootCA1*", "*root*CA*", "*RootCA*"])
    if propia:
        return propia
    incluida = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "AmazonRootCA1.pem"
    )
    return incluida if os.path.exists(incluida) else None


def identidad() -> tuple[str, str, str] | None:
    """Las tres rutas que necesita TLS, o None si falta alguna."""
    cert, llave, raiz = certificado(), llave_privada(), raiz_amazon()
    if cert and llave and raiz:
        return cert, llave, raiz
    return None


def archivo_politica_del_kit() -> str | None:
    """El archivo '...-Policy' que venía dentro del connection kit.

    Nos interesa por un motivo muy concreto: dentro lleva los ARN completos
    de tu cuenta, así que de ahí salen tu número de cuenta y tu región sin
    que tengas que copiarlos a mano de ninguna pantalla.
    """
    return _buscar(["*-Policy", "*-Policy.json", "*Policy*"])


def abandonar(motivo: str) -> None:
    """Sale del programa con un mensaje útil en vez de con un error de Python."""
    print(f"\n  {motivo}\n")
    print("  Ejecuta el diagnóstico para ver exactamente qué falta:\n")
    print("      docker compose run --rm dispositivo python comprobar.py\n")
    raise SystemExit(1)
