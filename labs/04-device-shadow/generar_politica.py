"""Escribe TU política, con tu número de cuenta y tu región ya puestos.

POR QUÉ EXISTE ESTE ARCHIVO
    La política del curso es igual para todos salvo en dos datos: el número
    de cuenta (12 dígitos) y la región. Son los que aparecen en cada ARN:

        arn:aws:iot:us-east-2:123456789012:topic/fablab/planta1/*
                    └─región─┘ └──cuenta──┘

    Copiarlos a mano de la consola funciona, pero con veinte personas en la
    sala garantiza dos o tres errores de un solo dígito. Y un error ahí no
    da un mensaje claro: da una conexión que se corta sin decir nada.

    Esos dos datos ya los tienes escritos: vinieron dentro de tu connection
    kit, en el archivo que termina en '-Policy'. Este script los lee de ahí
    y te escribe el JSON listo para pegar en la consola.

CÓMO SE EJECUTA
    docker compose run --rm dispositivo python generar_politica.py

LO QUE TIENES QUE SABER
    Esto NO cambia nada en AWS. Solo escribe un archivo en tu carpeta. Los
    permisos no se aplican hasta que tú pegues ese contenido en la consola
    y marques "establecer como versión activa".
"""

import json
import os
import re

import config

AQUI = os.path.dirname(os.path.abspath(__file__))

VERDE = "\033[92m"
ROJO = "\033[91m"
GRIS = "\033[90m"
FIN = "\033[0m"


def datos_de_la_cuenta() -> tuple[str, str] | None:
    """Saca (región, cuenta) del archivo -Policy del connection kit.

    Buscamos el primer ARN de IoT que aparezca y le pedimos sus dos campos.
    Un ARN tiene siempre la misma estructura, separada por dos puntos:

        arn : aws : iot : REGION : CUENTA : recurso
         0     1     2      3        4        5

    Vale la pena que te fijes, porque los ARN están en todo AWS y se leen
    siempre igual.
    """
    ruta = config.archivo_politica_del_kit()
    if not ruta:
        return None

    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    hallazgo = re.search(r"arn:aws:iot:([a-z0-9-]+):(\d{12}):", contenido)
    if not hallazgo:
        return None

    return hallazgo.group(1), hallazgo.group(2)


def main() -> None:
    print()

    datos = datos_de_la_cuenta()

    if datos:
        region, cuenta = datos
        origen = os.path.basename(config.archivo_politica_del_kit() or "")
        print(f"  Leído de {origen}:")
    else:
        # Plan B: la región está dentro del endpoint, pero el número de
        # cuenta no aparece en ningún otro sitio de la carpeta. Si llegamos
        # aquí, hay que pedirlo.
        region = config.region()
        print(f"  {ROJO}No encontré el archivo '-Policy' de tu connection kit.{FIN}")
        print(f"  {GRIS}Debería estar en la carpeta 'certificados', junto a tu{FIN}")
        print(f"  {GRIS}certificado. Si lo borraste, no pasa nada: el número de{FIN}")
        print(f"  {GRIS}cuenta está al principio de la URL de tu consola, y son{FIN}")
        print(f"  {GRIS}los 12 dígitos antes del primer guion.{FIN}\n")
        cuenta = input("  Escribe tu número de cuenta (12 dígitos): ").strip()

        if not re.fullmatch(r"\d{12}", cuenta):
            print(f"\n  {ROJO}Eso no son 12 dígitos. Vuelve a intentarlo.{FIN}\n")
            raise SystemExit(1)

    if not region:
        print(f"\n  {ROJO}No pude deducir tu región.{FIN}")
        print(f"  {GRIS}Revisa AWS_IOT_ENDPOINT en el .env del laboratorio 03.{FIN}\n")
        raise SystemExit(1)

    print(f"      región: {region}")
    print(f"      cuenta: {cuenta}")
    print(f"      objeto: {config.ID}")

    # --- La política del dispositivo ---------------------------------------
    plantilla = os.path.join(AQUI, "politica-curso-v2.json")
    with open(plantilla, "r", encoding="utf-8") as archivo:
        texto = archivo.read()

    texto = texto.replace("REGION", region).replace("CUENTA", cuenta)

    destino = os.path.join(AQUI, "mi-politica.json")
    with open(destino, "w", encoding="utf-8") as archivo:
        archivo.write(texto)

    # Lo validamos antes de dárselo: si la plantilla se rompió alguna vez,
    # mejor enterarnos aquí que en el editor de la consola.
    json.loads(texto)

    # --- La política del usuario de IAM ------------------------------------
    plantilla_iam = os.path.join(AQUI, "politica-app-iam.json")
    with open(plantilla_iam, "r", encoding="utf-8") as archivo:
        texto_iam = archivo.read()

    texto_iam = (
        texto_iam.replace("REGION", region)
        .replace("CUENTA", cuenta)
        .replace("MI-OBJETO", config.ID)
    )

    destino_iam = os.path.join(AQUI, "mi-politica-app.json")
    with open(destino_iam, "w", encoding="utf-8") as archivo:
        archivo.write(texto_iam)

    json.loads(texto_iam)

    # Lo imprimimos aquí mismo. Podríamos limitarnos a decir "está en el
    # archivo", pero entonces hay que explicar cómo se abre un .json en cada
    # sistema operativo, y ese rodeo atasca a media clase. Copiar de la
    # terminal funciona en todas partes.
    print(f"\n  {VERDE}Listo.{FIN} Esto es lo que tienes que pegar en la consola:\n")
    print(f"  {GRIS}IoT Core -> Security -> Policies -> tu política -> Edit -> JSON{FIN}")
    print(f"  {GRIS}(selecciona desde la llave de abajo hasta la última){FIN}")
    print()
    print("-" * 70)
    print(texto.strip())
    print("-" * 70)
    print()
    print(f"  {VERDE}Y marca «establecer como versión activa» antes de guardar.{FIN}")
    print(f"  {GRIS}Si no lo marcas, se crea una versión nueva que no se aplica{FIN}")
    print(f"  {GRIS}a nada: guarda bien, no da error, y no cambia nada.{FIN}")
    print()
    print("  También quedaron estos dos archivos en esta carpeta, por si")
    print("  prefieres copiarlos desde un editor:")
    print()
    print("      mi-politica.json       -> el CERTIFICADO de tu dispositivo")
    print("                                (IoT Core -> Security -> Policies)")
    print("      mi-politica-app.json   -> el USUARIO DE IAM de tu aplicación")
    print("                                (IAM -> Usuarios -> Permisos)")
    print()
    print(f"  {GRIS}Son dos identidades distintas y por eso son dos políticas{FIN}")
    print(f"  {GRIS}distintas: el dispositivo entra con un certificado, la{FIN}")
    print(f"  {GRIS}aplicación entra con claves. No se mezclan.{FIN}")
    print()


if __name__ == "__main__":
    main()
