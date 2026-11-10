"""Configuración compartida: encuentra tus certificados y tu endpoint.

POR QUÉ EXISTE ESTE ARCHIVO
    Los archivos del "connection kit" que descargas de AWS llevan el nombre
    de TU objeto delante (por ejemplo tanque-03.cert.pem), así que cada
    persona tiene nombres distintos. En vez de pedirte que escribas tres
    rutas a mano en cada script, los buscamos por su FORMA: el que acaba en
    .cert.pem es el certificado, el que acaba en .private.key es la llave,
    y así.

    No necesitas tocar nada de aquí. Está comentado para que lo entiendas,
    no para que lo edites: lo que se configura va en el archivo .env.
"""

from __future__ import annotations

import glob
import os

# ---------------------------------------------------------------------------
# Lo que viene de fuera (del archivo .env, a través de docker compose)
# ---------------------------------------------------------------------------
# os.getenv(nombre, por_defecto) lee una variable de entorno. Si no está
# definida, usa el segundo valor. Así el mismo código funciona dentro del
# contenedor y fuera de él.

# Dónde están tus certificados. Dentro del contenedor, docker monta la
# carpeta ./certificados en /certificados.
CARPETA = os.getenv("CARPETA_CERTIFICADOS", "/certificados")

# La dirección de TU cuenta de AWS. Consola: IoT Core -> Configuración ->
# "Punto de enlace de datos del dispositivo". Es distinta para cada persona
# y lleva la región dentro.
ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "").strip()

# El nombre del objeto que creaste en la consola. Se usa para tres cosas:
# como identificador de cliente al conectarse, para armar tus topics, y para
# elegir el certificado correcto si tienes varios kits en la carpeta.
ID = os.getenv("DISPOSITIVO_ID", "mi-dispositivo").strip()

# MQTT sobre TLS. En AWS IoT Core no existe el 1883 sin cifrar: o te
# identificas con un certificado, o no entras.
PUERTO = 8883

# Los dos topics del laboratorio. Fíjate en la estructura: de lo general a
# lo específico, y el identificador del dispositivo dentro. La política solo
# autoriza lo que cuelgue de fablab/planta1/.
TOPIC_TELEMETRIA = f"fablab/planta1/{ID}/telemetria"
TOPIC_COMANDOS = f"fablab/planta1/{ID}/comandos"


# ---------------------------------------------------------------------------
# Localizar los archivos
# ---------------------------------------------------------------------------


def _buscar(patrones: list[str], excluir: str | None = None) -> str | None:
    """Devuelve el archivo de la carpeta que encaje con algún patrón.

    Los patrones se prueban en orden, del más específico al más general: así
    "*.cert.pem" gana antes de llegar a un "*.crt" que podría coincidir con
    otra cosa.

    Si has creado más de un dispositivo y tienes varios kits en la misma
    carpeta, gana el que lleva el nombre del dispositivo que estás usando
    (DISPOSITIVO_ID). Sin esto elegiría el primero por orden alfabético, y
    el error sería incomprensible: credenciales de un objeto, nombre de otro.
    """
    for patron in patrones:
        encontrados = sorted(glob.glob(os.path.join(CARPETA, patron)))

        # Algunos patrones son tan amplios que podrían pescar un archivo que
        # no queremos (la llave pública, por ejemplo).
        if excluir:
            encontrados = [r for r in encontrados if excluir not in os.path.basename(r).lower()]

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
    # El kit trae también una llave PÚBLICA con un nombre casi idéntico. Si
    # las confundiéramos, el error de TLS sería incomprensible, así que la
    # descartamos de forma explícita.
    return _buscar(
        ["*private.pem.key", "*-private.pem", "*.private.key", "*.key"],
        excluir="public",
    )


def raiz_amazon() -> str | None:
    """El certificado raíz de Amazon: con él comprobamos que el servidor es AWS."""
    # El kit de conexión NO lo incluye: su script lo descarga aparte. Para que
    # nadie se quede atascado, el laboratorio ya lo trae (es un certificado
    # público, el mismo para todo el mundo). Si tú descargaste uno, gana el
    # tuyo; si no, usamos el que acompaña a estos scripts.
    propia = _buscar(["*AmazonRootCA1*", "*root*CA*", "*RootCA*"])
    if propia:
        return propia
    incluida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AmazonRootCA1.pem")
    return incluida if os.path.exists(incluida) else None


def identidad() -> tuple[str, str, str] | None:
    """Las tres rutas que necesita TLS, o None si falta alguna.

    Los tres archivos van siempre juntos: sin el certificado no sabes quién
    eres, sin la llave no puedes demostrarlo, y sin el raíz no puedes
    comprobar que el servidor es quien dice ser.
    """
    cert, llave, raiz = certificado(), llave_privada(), raiz_amazon()
    if cert and llave and raiz:
        return cert, llave, raiz
    return None


def abandonar(motivo: str) -> None:
    """Sale del programa con un mensaje útil en vez de con un error de Python.

    Un traceback de 20 líneas no le dice nada a quien empieza. Preferimos
    decir qué falta y a dónde ir.
    """
    print(f"\n  {motivo}\n")
    print("  Ejecuta el diagnóstico para ver exactamente qué falta:\n")
    print("      docker compose run --rm aws python comprobar.py\n")
    raise SystemExit(1)
