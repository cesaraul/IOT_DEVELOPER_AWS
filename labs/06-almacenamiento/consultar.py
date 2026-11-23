"""Leer de DynamoDB lo que la regla fue guardando.

CÓMO SE EJECUTA
    docker compose run --rm app python consultar.py
    docker compose run --rm app python consultar.py 20
    docker compose run --rm app python consultar.py --rango 10:00 10:30

LO IMPORTANTE DE ESTE ARCHIVO
    Aquí se ve para qué sirvió elegir bien la clave de la tabla.

    Pedir "las últimas diez lecturas de este equipo" no recorre nada: va
    directo. Y pedir "las de entre las 10:00 y las 10:30" tampoco, porque
    dentro de cada dispositivo las filas están ORDENADAS por el campo
    'momento', que es la clave de ordenación.

    Esa es toda la diferencia entre query y scan, y es la razón por la
    que DynamoDB responde igual de rápido con diez filas que con diez
    millones.
"""

import sys
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

import config

config.exigir_claves()

tabla = boto3.resource("dynamodb", region_name=config.REGION).Table(config.TABLA)


def hoy(hora: str) -> str:
    """Convierte '10:30' en la marca de tiempo completa de hoy.

    Las filas se guardan con un texto tipo 2026-11-23T10:30:00.000Z. Como
    ese formato ordena igual que el tiempo —primero el año, luego el mes,
    luego el día—, comparar textos es comparar fechas. Por eso la clave
    de ordenación es texto y no un número.
    """
    dia = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{dia}T{hora}:00.000Z"


def mostrar(filas: list) -> None:
    if not filas:
        print(f"\n  {config.GRIS}Ninguna fila.{config.FIN}\n")
        print("  Si acabas de desplegar, dale un minuto: la regla guarda")
        print("  cada mensaje, pero el dispositivo publica cada 10 segundos.")
        print("  Y comprueba que el dispositivo está encendido.\n")
        return

    print(f"\n  {len(filas)} fila(s) de '{config.ID}'\n")
    print(f"  {'momento':<26} {'nivel':>7} {'temp':>7}   alarma")
    print(f"  {'-' * 26} {'-' * 7} {'-' * 7}   ------")

    for f in filas:
        # Los números vienen como Decimal: DynamoDB no usa coma flotante
        # para no perder precisión. Hay que convertirlos para imprimirlos.
        nivel = float(f.get("nivel", 0))
        temp = float(f.get("temp", 0))
        alarma = "SI" if f.get("alarma") else ""
        color = config.ROJO if f.get("alarma") else ""
        fin = config.FIN if f.get("alarma") else ""
        print(
            f"  {f.get('momento', '?'):<26} {nivel:>7.1f} {temp:>7.1f}   "
            f"{color}{alarma}{fin}"
        )
    print()


def main() -> None:
    args = sys.argv[1:]

    # --- Modo rango: entre dos horas de hoy ------------------------------
    if args and args[0] == "--rango":
        if len(args) < 3:
            print("\n  Uso:  consultar.py --rango 10:00 10:30\n")
            raise SystemExit(1)

        desde, hasta = hoy(args[1]), hoy(args[2])
        print(f"\n  Buscando entre {args[1]} y {args[2]} UTC...")

        r = tabla.query(
            # La condición de la clave: el dispositivo exacto, y el
            # momento dentro de un rango. Esto NO recorre la tabla.
            KeyConditionExpression=Key("dispositivo").eq(config.ID)
            & Key("momento").between(desde, hasta)
        )
        mostrar(r["Items"])
        return

    # --- Modo por defecto: las últimas N ---------------------------------
    cuantas = int(args[0]) if args else 10

    r = tabla.query(
        KeyConditionExpression=Key("dispositivo").eq(config.ID),
        # Al revés: de la más nueva a la más vieja.
        ScanIndexForward=False,
        Limit=cuantas,
    )
    mostrar(r["Items"])

    print(f"  {config.GRIS}Prueba también:{config.FIN}")
    print(f"  {config.GRIS}  consultar.py 30{config.FIN}")
    print(f"  {config.GRIS}  consultar.py --rango 10:00 10:30{config.FIN}\n")


if __name__ == "__main__":
    main()
