"""Configuración compartida: encuentra tus certificados y tu endpoint.

Los archivos del "connection kit" de AWS traen nombres distintos para cada
persona (empiezan por el nombre de tu Thing), así que en vez de pedirte que
escribas tres rutas a mano, los buscamos por su forma.

No necesitas tocar este archivo.
"""

from __future__ import annotations

import glob
import os

CARPETA = os.getenv("CARPETA_CERTIFICADOS", "/certificados")
ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "").strip()
ID = os.getenv("DISPOSITIVO_ID", "mi-dispositivo").strip()
PUERTO = 8883  # MQTT sobre TLS. El 1883 sin cifrar no existe en AWS.

TOPIC_TELEMETRIA = f"fablab/planta1/{ID}/telemetria"
TOPIC_COMANDOS = f"fablab/planta1/{ID}/comandos"


def _buscar(patrones: list[str], excluir: str | None = None) -> str | None:
    """Devuelve el primer archivo de la carpeta que encaje con algún patrón."""
    for patron in patrones:
        encontrados = sorted(glob.glob(os.path.join(CARPETA, patron)))
        if excluir:
            encontrados = [r for r in encontrados if excluir not in os.path.basename(r).lower()]
        if encontrados:
            return encontrados[0]
    return None


def certificado() -> str | None:
    return _buscar(["*certificate.pem.crt", "*-certificate.pem", "*.cert.pem", "*.crt"])


def llave_privada() -> str | None:
    # El kit trae también una llave PÚBLICA con un nombre parecido: si la
    # confundiéramos, el error de TLS sería incomprensible.
    return _buscar(
        ["*private.pem.key", "*-private.pem", "*.private.key", "*.key"],
        excluir="public",
    )


def raiz_amazon() -> str | None:
    return _buscar(["*AmazonRootCA1*", "*root*CA*.pem", "*RootCA*"])


def identidad() -> tuple[str, str, str] | None:
    """Las tres rutas que necesita TLS, o None si falta alguna."""
    cert, llave, raiz = certificado(), llave_privada(), raiz_amazon()
    if cert and llave and raiz:
        return cert, llave, raiz
    return None


def abandonar(motivo: str) -> None:
    """Sale con un mensaje útil en vez de con un error de Python."""
    print(f"\n  {motivo}\n")
    print("  Ejecuta el diagnóstico para ver exactamente qué falta:\n")
    print("      docker compose run --rm aws python comprobar.py\n")
    raise SystemExit(1)
