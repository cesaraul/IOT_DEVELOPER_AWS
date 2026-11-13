"""La aplicación: da órdenes al dispositivo, sin ser un dispositivo.

QUÉ HACE
    Escribe el estado DESEADO en el shadow. Eso es todo. No se conecta al
    dispositivo, no sabe si está encendido, y no le importa: deja la orden
    escrita y sigue con su vida. Cuando el equipo aparezca, obedecerá.

CÓMO SE EJECUTA
    docker compose run --rm app python shadow_app.py ver
    docker compose run --rm app python shadow_app.py encender
    docker compose run --rm app python shadow_app.py apagar
    docker compose run --rm app python shadow_app.py umbral 60

LO IMPORTANTE DE ESTE ARCHIVO — LÉELO AUNQUE NO LEAS EL RESTO
    Compara las primeras líneas de código con las de shadow_dispositivo.py.
    Hacen cosas parecidas contra el mismo shadow, pero entran a AWS por
    puertas distintas:

                      | DISPOSITIVO              | APLICACIÓN (esto)
    ------------------|--------------------------|-------------------------
    Quién es          | el equipo en la planta   | un backend, una web
    Se identifica con | certificado X.509        | claves de un usuario IAM
    Habla por         | MQTT, puerto 8883        | API HTTPS de AWS
    Librería          | paho-mqtt                | boto3 (el SDK de AWS)
    Escribe           | 'reported'               | 'desired'

    ¿Por qué no usar el certificado del dispositivo aquí y ahorrarse el
    usuario de IAM? Porque una aplicación no es un dispositivo. Si tu
    backend lleva dentro el certificado del sensor, cualquiera que entre al
    backend puede hacerse pasar por ese sensor — y si mañana retiras el
    sensor y revocas su certificado, tu backend deja de funcionar. Dos
    actores, dos identidades. Esta es la regla, y no es de IoT: es de AWS
    entero.
"""

import json
import sys

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

import config

VERDE = "\033[92m"
ROJO = "\033[91m"
GRIS = "\033[90m"
FIN = "\033[0m"


def cliente():
    """Crea el cliente del SDK contra el plano de datos de IoT Core.

    Dos detalles que no se adivinan:

    1. El servicio se llama 'iot-data', no 'iot'. Son dos APIs distintas:
       'iot' sirve para administrar (crear objetos, políticas, certificados)
       y 'iot-data' para hablar con los dispositivos y sus shadows. Pedirle
       un shadow al cliente equivocado da un error que no ayuda nada.

    2. Hay que darle el endpoint a mano. Es el MISMO que usa el dispositivo
       por MQTT, pero aquí va con https:// delante, porque esto no es MQTT:
       es una llamada HTTP normal y corriente, firmada con tus claves.

    Las credenciales no se pasan: boto3 las busca solo en las variables de
    entorno AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY, que vienen de tu .env.
    Por eso no verás ninguna clave escrita en este archivo, y por eso este
    archivo sí puede estar en un repositorio público.
    """
    return boto3.client(
        "iot-data",
        region_name=config.region(),
        endpoint_url=f"https://{config.ENDPOINT}",
    )


def leer(iot) -> dict:
    """Trae el documento completo del shadow."""
    respuesta = iot.get_thing_shadow(thingName=config.ID)
    # El cuerpo viene como un flujo de bytes, no como texto ya listo.
    return json.loads(respuesta["payload"].read())


def desear(iot, cambios: dict) -> None:
    """Escribe el estado deseado. Esto es dar la orden.

    Solo mandamos lo que queremos cambiar. AWS lo mezcla con lo que ya
    había: si pides {"bomba": "encendida"}, el umbral que estuviera puesto
    se queda como estaba. No hace falta reenviar el documento entero.
    """
    mensaje = {"state": {"desired": cambios}}
    iot.update_thing_shadow(thingName=config.ID, payload=json.dumps(mensaje))

    print(f"\n  {VERDE}Orden enviada:{FIN} {cambios}")
    print(f"  {GRIS}Queda escrita en el shadow. Si el equipo está apagado,{FIN}")
    print(f"  {GRIS}la cumplirá en cuanto encienda.{FIN}\n")


def mostrar(documento: dict) -> None:
    """Imprime el shadow de forma legible, con las dos columnas enfrentadas."""
    estado = documento.get("state", {})
    deseado = estado.get("desired", {})
    reportado = estado.get("reported", {})
    delta = estado.get("delta", {})

    claves = sorted(set(deseado) | set(reportado))

    print(f"\n  Shadow de '{config.ID}' (versión {documento.get('version')})\n")
    print(f"  {'campo':<12} {'deseado':<14} {'reportado':<14}")
    print(f"  {'-' * 12} {'-' * 14} {'-' * 14}")

    for clave in claves:
        marca = "  <- pendiente" if clave in delta else ""
        d = str(deseado.get(clave, "—"))
        r = str(reportado.get(clave, "—"))
        print(f"  {clave:<12} {d:<14} {r:<14}{marca}")

    if delta:
        print(f"\n  {ROJO}Hay diferencias.{FIN} El equipo todavía no ha obedecido")
        print(f"  {GRIS}(o está apagado, que es lo mismo visto desde aquí).{FIN}")
    else:
        print(f"\n  {VERDE}Todo coincide.{FIN} El equipo está como lo pediste.")
    print()


def ayuda() -> None:
    print(__doc__.split("LO IMPORTANTE")[0].strip())
    print()


def main() -> None:
    if not config.CLAVE_ID or not config.CLAVE_SECRETA:
        print(f"\n  {ROJO}Faltan las claves del usuario de IAM.{FIN}")
        print("\n  Esta parte del laboratorio NO usa el certificado: la")
        print("  aplicación entra a AWS con su propia identidad.")
        print("\n  Cópialas en el archivo .env de esta carpeta:")
        print("      AWS_ACCESS_KEY_ID=...")
        print("      AWS_SECRET_ACCESS_KEY=...")
        print("\n  Se crean en: IAM -> Usuarios -> tu usuario ->")
        print("  Credenciales de seguridad -> Crear clave de acceso.\n")
        raise SystemExit(1)

    if len(sys.argv) < 2:
        ayuda()
        raise SystemExit(1)

    orden = sys.argv[1].lower()
    iot = cliente()

    try:
        if orden == "ver":
            mostrar(leer(iot))

        elif orden == "encender":
            desear(iot, {"bomba": "encendida"})

        elif orden == "apagar":
            desear(iot, {"bomba": "apagada"})

        elif orden == "umbral":
            if len(sys.argv) < 3:
                print("\n  Dime el número:  shadow_app.py umbral 60\n")
                raise SystemExit(1)
            desear(iot, {"umbral": int(sys.argv[2])})

        else:
            ayuda()
            raise SystemExit(1)

    except NoCredentialsError:
        print(f"\n  {ROJO}boto3 no encontró tus claves.{FIN}")
        print("  Revisa el .env de esta carpeta.\n")
        raise SystemExit(1)

    except ClientError as error:
        codigo = error.response["Error"]["Code"]

        if codigo == "ResourceNotFoundException":
            print(f"\n  {ROJO}Ese objeto no tiene shadow todavía.{FIN}")
            print("  El shadow no existe hasta que alguien escribe en él.")
            print("  Arranca primero el dispositivo:\n")
            print("      docker compose run --rm dispositivo python shadow_dispositivo.py\n")

        elif codigo in ("AccessDeniedException", "ForbiddenException"):
            print(f"\n  {ROJO}Tu usuario de IAM no tiene permiso para esto.{FIN}")
            print("  Necesita iot:GetThingShadow e iot:UpdateThingShadow.")
            print("  Genera su política con:\n")
            print("      docker compose run --rm dispositivo python generar_politica.py\n")
            print("  y pégala en IAM -> Usuarios -> tu usuario -> Permisos.\n")

        elif codigo in ("UnrecognizedClientException", "InvalidSignatureException"):
            print(f"\n  {ROJO}AWS no reconoce esas claves.{FIN}")
            print("  Suele ser un copiar-pegar incompleto, o una clave que")
            print("  ya borraste. Crea una nueva y vuelve a ponerla en .env.\n")

        else:
            print(f"\n  {ROJO}AWS devolvió {codigo}:{FIN}")
            print(f"  {error.response['Error']['Message']}\n")

        raise SystemExit(1)


if __name__ == "__main__":
    main()
