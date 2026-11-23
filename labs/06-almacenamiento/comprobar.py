"""Diagnóstico: ¿está todo lo de la clase 6 en su sitio?

CÓMO SE EJECUTA
    docker compose run --rm app python comprobar.py

QUÉ COMPRUEBA, Y EN ESE ORDEN
    De lo más cercano a lo más lejano, para que el primer fallo sea
    siempre el verdadero y no un síntoma:

    1. Tus claves          están puestas y AWS las acepta
    2. La tabla            existe, y en qué modo de capacidad
    3. El bucket           existe
    4. La regla            existe, está activa y tiene las dos acciones
    5. ¿Llega algo?        hay filas en la tabla y archivos en el bucket

    El 5 es distinto de los demás: si falla, no está roto nada — lo más
    probable es que el dispositivo no esté encendido.
"""

import sys

import boto3
from botocore.exceptions import ClientError

import config

VERDE, ROJO, GRIS, FIN = config.VERDE, config.ROJO, config.GRIS, config.FIN

fallos = 0


def bien(t: str) -> None:
    print(f"  {VERDE}OK{FIN}    {t}")


def mal(t: str, arreglo: str) -> None:
    global fallos
    fallos += 1
    print(f"  {ROJO}FALTA{FIN} {t}")
    for linea in arreglo.strip().splitlines():
        print(f"        {GRIS}{linea.strip()}{FIN}")


def aviso(t: str, nota: str) -> None:
    print(f"  {GRIS}·{FIN}     {t}")
    for linea in nota.strip().splitlines():
        print(f"        {GRIS}{linea.strip()}{FIN}")


def titulo(t: str) -> None:
    print(f"\n{t}")
    print("-" * 66)


# --- 1. Las claves --------------------------------------------------------

titulo("1. Tus claves de IAM")

if not config.CLAVE_ID or not config.CLAVE_SECRETA:
    mal(
        "no están puestas",
        """Van en el archivo .env de esta carpeta.
           Cómo se crean: docs/acceso-desde-tu-laptop.md""",
    )
else:
    bien(f"clave: {config.CLAVE_ID[:4]}...{config.CLAVE_ID[-4:]}")
    try:
        yo = boto3.client("sts", region_name=config.REGION).get_caller_identity()
        bien(f"AWS te reconoce: {yo['Arn'].split('/')[-1]} (cuenta {yo['Account']})")
    except Exception as e:
        mal(
            f"AWS no acepta esas claves ({type(e).__name__})",
            """Suele ser un copiar-pegar incompleto, o una clave borrada.
               Crea una nueva en IAM y vuelve a ponerla en el .env.""",
        )

print(f"  {GRIS}región: {config.REGION}{FIN}")

# --- 2. La tabla ----------------------------------------------------------

hay_tabla = False

if fallos == 0:
    titulo("2. La tabla de DynamoDB")
    ddb = boto3.client("dynamodb", region_name=config.REGION)
    try:
        t = ddb.describe_table(TableName=config.TABLA)["Table"]
        hay_tabla = True
        bien(f"existe: {config.TABLA}")

        claves = {k["KeyType"]: k["AttributeName"] for k in t["KeySchema"]}
        bien(f"clave de partición: {claves.get('HASH')}")
        bien(f"clave de ordenación: {claves.get('RANGE')}")

        modo = t.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")
        if modo == "PROVISIONED":
            bien("modo aprovisionado (dentro del Free Tier permanente)")
        else:
            aviso(
                "la tabla está en modo BAJO DEMANDA",
                """Funciona, pero se paga desde la primera escritura: el
                   Free Tier permanente de DynamoDB solo cubre el modo
                   aprovisionado. Son céntimos en el curso.""",
            )

    except ddb.exceptions.ResourceNotFoundException:
        mal(
            f"no existe la tabla '{config.TABLA}'",
            """¿Desplegaste la plantilla?
               aws cloudformation deploy --template-file infra/clase6.yaml
                 --stack-name clase6 --capabilities CAPABILITY_NAMED_IAM
               Y comprueba que TABLA en el .env coincide con el Output.""",
        )

# --- 3. El bucket ---------------------------------------------------------

hay_bucket = False

if fallos == 0:
    titulo("3. El bucket de S3")
    if not config.BUCKET:
        mal(
            "no has puesto el nombre del bucket",
            """Lo dice la plantilla al desplegarla, en los Outputs.
               Ponlo en el .env:  BUCKET=...""",
        )
    else:
        s3 = boto3.client("s3", region_name=config.REGION)
        try:
            s3.head_bucket(Bucket=config.BUCKET)
            hay_bucket = True
            bien(f"existe: {config.BUCKET}")
        except ClientError as e:
            mal(
                f"no puedo abrir el bucket ({e.response['Error']['Code']})",
                """Comprueba el nombre en el .env. Lleva tu número de
                   cuenta al final, así que no se puede adivinar.""",
            )

# --- 4. La regla ----------------------------------------------------------

if fallos == 0:
    titulo("4. La regla que guarda")
    iot = boto3.client("iot", region_name=config.REGION)
    nombre = config.ID.replace("-", "_") + "_guardar"
    try:
        r = iot.get_topic_rule(ruleName=nombre)["rule"]
        bien(f"existe: {nombre}")

        if r.get("ruleDisabled"):
            mal(
                "la regla está DESACTIVADA",
                "Actívala: aws iot enable-topic-rule --rule-name " + nombre,
            )
        else:
            bien("está activa")

        acciones = [list(a.keys())[0] for a in r["actions"]]
        if "dynamoDBv2" in acciones:
            bien("escribe en la tabla")
        else:
            mal("no tiene acción de DynamoDB", "Revisa la plantilla.")
        if "s3" in acciones:
            bien("escribe en el bucket")
        else:
            mal("no tiene acción de S3", "Revisa la plantilla.")

        if "WHERE" in r["sql"].upper():
            aviso(
                "la regla lleva WHERE",
                """La de guardar no debería filtrar: lo que descartes hoy
                   no se recupera mañana. Filtrar es para la de avisar.""",
            )
        else:
            bien("no lleva WHERE: guarda todo, que es lo que toca")

    except iot.exceptions.UnauthorizedException:
        mal("tus claves no pueden leer las reglas de IoT", "Revisa los permisos.")
    except Exception:
        mal(
            f"no encuentro la regla '{nombre}'",
            """Se llama como tu dispositivo con _guardar al final, y con
               guiones bajos. Comprueba DISPOSITIVO_ID en el .env.""",
        )

# --- 5. ¿Está llegando algo? ---------------------------------------------

if fallos == 0:
    titulo("5. ¿Está entrando algo?")

    if hay_tabla:
        n = boto3.client("dynamodb", region_name=config.REGION).describe_table(
            TableName=config.TABLA
        )["Table"]["ItemCount"]
        if n:
            bien(f"la tabla tiene del orden de {n} fila(s)")
        else:
            aviso(
                "la tabla parece vacía",
                """El contador de DynamoDB se actualiza cada pocas horas,
                   así que puede mentir al principio. Míralo de verdad:
                   python consultar.py""",
            )

    if hay_bucket:
        r = boto3.client("s3", region_name=config.REGION).list_objects_v2(
            Bucket=config.BUCKET, MaxKeys=5
        )
        if r.get("KeyCount"):
            bien(f"el bucket ya tiene archivos ({r['KeyCount']}+)")
        else:
            aviso(
                "el bucket está vacío",
                """Si acabas de desplegar, dale un minuto. Y comprueba que
                   el dispositivo esté encendido:
                   cd ../04-device-shadow
                   docker compose run --rm dispositivo python shadow_dispositivo.py""",
            )

# --- Resumen --------------------------------------------------------------

print()
if fallos == 0:
    print(f"  {VERDE}Todo en su sitio.{FIN} Ahora mira los datos:\n")
    print("      docker compose run --rm app python consultar.py")
    print("      docker compose run --rm app python explorar.py\n")
    sys.exit(0)

print(f"  {ROJO}Hay {fallos} cosa(s) por arreglar.{FIN} Corrige y vuelve a ejecutar.\n")
sys.exit(1)
