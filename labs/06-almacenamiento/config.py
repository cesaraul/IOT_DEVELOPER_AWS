"""Configuración compartida del laboratorio 06.

QUÉ CAMBIA RESPECTO A LOS LABORATORIOS ANTERIORES
    Aquí NO hay certificados. Ni uno.

    Los laboratorios 03, 04 y 05 se conectaban como el DISPOSITIVO, con su
    certificado X.509, por MQTT. Estos scripts no son el dispositivo: son
    una APLICACIÓN que consulta lo que quedó guardado, y entran a AWS con
    las claves de tu usuario de IAM, por HTTPS.

    Es la misma distinción de la clase 4, ahora del todo separada: el
    equipo escribe, tú lees, y cada uno entra por su puerta.
"""

from __future__ import annotations

import os
import sys

# Las claves del usuario de IAM. boto3 las lee solo de estas variables;
# las nombramos aquí únicamente para poder avisar con un mensaje claro
# cuando falten.
CLAVE_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
CLAVE_SECRETA = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

# La región. Tiene que ser la misma donde desplegaste la plantilla, o no
# vas a encontrar nada: los recursos de una región no se ven desde otra.
REGION = os.getenv("AWS_REGION", "us-east-2").strip()

# El nombre de tu dispositivo, para filtrar sus filas.
ID = os.getenv("DISPOSITIVO_ID", "mi-dispositivo").strip()

# La tabla y el bucket. Los dice la plantilla al terminar de desplegar,
# en la sección Outputs.
TABLA = os.getenv("TABLA", f"{ID}-telemetria").strip()
BUCKET = os.getenv("BUCKET", "").strip()

VERDE = "\033[92m"
ROJO = "\033[91m"
GRIS = "\033[90m"
FIN = "\033[0m"


def exigir_claves() -> None:
    """Para con un mensaje útil si faltan las credenciales.

    Un traceback de boto3 no le dice nada a quien empieza. Preferimos
    decir qué falta y dónde se consigue.
    """
    if CLAVE_ID and CLAVE_SECRETA:
        return

    print(f"\n  {ROJO}Faltan las claves de tu usuario de IAM.{FIN}\n")
    print("  Cópialas en el archivo .env de esta carpeta:")
    print("      AWS_ACCESS_KEY_ID=...")
    print("      AWS_SECRET_ACCESS_KEY=...")
    print("\n  Si todavía no tienes usuario, está explicado en")
    print("  docs/acceso-desde-tu-laptop.md\n")
    sys.exit(1)


def exigir_bucket() -> None:
    """El bucket no se puede adivinar: lleva el número de cuenta dentro."""
    if BUCKET:
        return

    print(f"\n  {ROJO}Falta el nombre del bucket.{FIN}\n")
    print("  Lo dice la plantilla al desplegarla, en los Outputs.")
    print("  O míralo con:  aws cloudformation describe-stacks \\")
    print("                   --stack-name clase6 --query 'Stacks[0].Outputs'")
    print("\n  Ponlo en el .env:   BUCKET=...\n")
    sys.exit(1)
