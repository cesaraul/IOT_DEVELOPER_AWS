"""Mirar qué hay en el bucket, y abrir uno de los archivos.

CÓMO SE EJECUTA
    docker compose run --rm app python explorar.py
    docker compose run --rm app python explorar.py --abrir LA/CLAVE/COMPLETA.json

LO IMPORTANTE DE ESTE ARCHIVO
    Compáralo con consultar.py y tendrás la clase entera.

    Allí pedías "las últimas diez del tanque-01" y DynamoDB iba directo.
    Aquí no se puede pedir eso: S3 solo sabe listar nombres y entregar
    archivos. Si quisieras "los mensajes donde el nivel pasó de 90",
    tendrías que bajarte todos y mirarlos uno por uno.

    Eso no es un defecto de S3: es lo que lo hace diez veces más barato.
    Guarda muchísimo por muy poco, a cambio de no saber buscar dentro.

    Para preguntarle cosas a lo que hay en S3 existe Athena, y eso es la
    clase 7.
"""

import json
import sys

import boto3

import config

config.exigir_claves()
config.exigir_bucket()

s3 = boto3.client("s3", region_name=config.REGION)


def abrir(clave: str) -> None:
    """Descarga un objeto y lo imprime."""
    print(f"\n  {clave}\n")
    cuerpo = s3.get_object(Bucket=config.BUCKET, Key=clave)["Body"].read()
    try:
        print(json.dumps(json.loads(cuerpo), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(cuerpo.decode(errors="replace"))
    print()


def listar() -> None:
    """Lista lo que hay, y enseña cómo están organizadas las carpetas."""
    # S3 no tiene carpetas de verdad: lo que parecen carpetas son barras
    # dentro del nombre del archivo. Nuestra regla los nombra así:
    #
    #     tanque-01/2026/11/23/a1b2c3....json
    #     └ equipo ┘└── fecha ──┘└ nombre único ┘
    #
    # Organizarlo por fecha no es estética: es lo que permite despues
    # leer "solo marzo" sin tocar el resto.
    r = s3.list_objects_v2(Bucket=config.BUCKET, MaxKeys=1000)

    objetos = r.get("Contents", [])
    if not objetos:
        print(f"\n  {config.GRIS}El bucket está vacío.{config.FIN}\n")
        print("  Si acabas de desplegar, dale un minuto. Y comprueba que")
        print("  el dispositivo esté encendido y publicando.\n")
        return

    total = len(objetos)
    bytes_totales = sum(o["Size"] for o in objetos)

    print(f"\n  {total} archivo(s) en {config.BUCKET}")
    print(f"  {bytes_totales} bytes en total")
    if r.get("IsTruncated"):
        print(f"  {config.GRIS}(hay más: esto son los primeros 1000){config.FIN}")

    # Las carpetas de primer nivel: un equipo por carpeta.
    equipos = sorted({o["Key"].split("/")[0] for o in objetos})
    print(f"\n  Equipos: {', '.join(equipos)}")

    print("\n  Los más recientes:\n")
    recientes = sorted(objetos, key=lambda o: o["LastModified"], reverse=True)[:8]
    for o in recientes:
        print(f"    {o['Size']:>5} B   {o['Key']}")

    print(f"\n  {config.GRIS}Abre uno con:{config.FIN}")
    print(f"  {config.GRIS}  explorar.py --abrir {recientes[0]['Key']}{config.FIN}\n")

    # El contraste con DynamoDB, dicho donde se nota.
    print(f"  {config.GRIS}Fíjate: aquí no puedes preguntar «¿cuáles pasaron")
    print(f"  de 90?». S3 solo lista nombres y entrega archivos.{config.FIN}\n")


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] == "--abrir":
        if len(args) < 2:
            print("\n  Uso:  explorar.py --abrir LA/CLAVE/COMPLETA.json\n")
            raise SystemExit(1)
        abrir(args[1])
        return

    listar()


if __name__ == "__main__":
    main()
