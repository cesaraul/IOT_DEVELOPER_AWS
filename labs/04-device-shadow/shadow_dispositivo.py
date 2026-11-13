"""El dispositivo: transmite datos y obedece al shadow.

QUÉ HACE
    Simula un tanque con una bomba. Hace las DOS cosas que hace un equipo
    real, a la vez y por la misma conexión:

        TELEMETRÍA   publica el nivel y la temperatura cada pocos segundos
                     en  fablab/planta1/TU-ID/telemetria
        ESTADO       obedece lo que diga su shadow: si la bomba va encendida,
                     cada cuántos segundos transmite, y a partir de qué nivel
                     hay alarma

    Y aquí está lo interesante: **el shadow gobierna la telemetría**. Si
    enciendes la bomba desde la consola, el nivel del tanque empieza a subir
    en los datos que ves llegar. Si cambias el intervalo, cambia el ritmo.
    El estado es la perilla; la telemetría es el efecto.

CÓMO SE EJECUTA
    docker compose run --rm dispositivo python shadow_dispositivo.py

    Y en la consola de AWS, para ver los datos:
        IoT Core -> Probar -> Cliente de prueba de MQTT
        suscríbete a  fablab/#

    Para detenerlo: Ctrl + C   (y eso es parte del laboratorio: apágalo,
    cámbiale el estado deseado desde la consola, y vuelve a encenderlo.
    Obedecerá.)

LA DISTINCIÓN QUE HAY QUE LLEVARSE
    Mira los dos topics en los que escribe este programa:

        fablab/planta1/TU-ID/telemetria    <- lo inventaste tú
        $aws/things/TU-ID/shadow/update    <- lo impone AWS

    El primero lleva MEDICIONES: muchas, seguidas, y si pierdes una no pasa
    nada porque en cinco segundos viene otra. AWS no las guarda: pasan.

    El segundo lleva ESTADO: cambia poco, y lo que diga ahí es la verdad
    hasta nuevo aviso. AWS sí lo guarda.

    Meter telemetría en el shadow es el error de diseño más común al
    empezar: se paga por operación, el documento tiene un límite de 8 KB, y
    encima solo te quedarías con el último valor. Y al revés, mandar la
    configuración como mensajes sueltos te deja sin saber en qué estado
    está el equipo cuando se reconecta.

EL CICLO DEL SHADOW
    1. Me suscribo a las respuestas.      <- ANTES de pedir nada
    2. Pido el documento completo (/get). <- por si me perdí algo apagado
    3. Aplico lo que diga.
    4. Reporto lo que soy ahora.
    5. Me quedo escuchando deltas mientras transmito.

LAS TRES REGLAS DEL SHADOW
    - El dispositivo escribe 'reported'. Nunca 'desired'.
    - La aplicación escribe 'desired'. Nunca 'reported'.
    - El 'delta' no lo escribe nadie: lo calcula AWS.

    Busca la palabra 'desired' en los publish de este archivo: no aparece.
"""

import json
import random
import ssl
import time

import paho.mqtt.client as mqtt

import config

# ---------------------------------------------------------------------------
# El estado del equipo: lo que se puede CONFIGURAR desde la nube
# ---------------------------------------------------------------------------
# Esto es lo que va al shadow. Son pocas cosas, cambian poco, y deben
# sobrevivir a un apagón.

estado = {
    "bomba": "apagada",   # encendida -> el tanque se llena; apagada -> se vacía
    "umbral": 80,         # a partir de este nivel, la telemetría marca alarma
    "intervalo": 5,       # cada cuántos segundos se transmite
}

# ---------------------------------------------------------------------------
# La realidad física: lo que se MIDE
# ---------------------------------------------------------------------------
# Esto NO va al shadow. Es una medición: cambia a cada segundo y lo que nos
# interesa de ella es la serie completa, no el último valor. Va por el topic
# de telemetría, como en el laboratorio 03.

nivel = 50.0

confirmadas = 0          # cuántas suscripciones ha confirmado AWS
ultimo_envio = 0.0       # cuándo transmitimos por última vez
listo = False            # ¿ya sabemos qué estado debemos tener?

rutas = config.identidad()
if not rutas:
    config.abandonar("Faltan los certificados. ¿Hiciste el laboratorio 03?")
if not config.ENDPOINT:
    config.abandonar("Falta tu endpoint. Revisa el .env del laboratorio 03.")

CERTIFICADO, LLAVE, RAIZ = rutas


# ---------------------------------------------------------------------------
# La parte de telemetría
# ---------------------------------------------------------------------------


def medir() -> dict:
    """Toma una lectura del tanque.

    Aquí es donde leerías el hardware de verdad. Lo que simulamos tiene una
    propiedad que importa para la clase: **el nivel depende de la bomba**.
    Así, cuando cambies el shadow desde la consola, lo vas a ver en los
    datos que llegan. El estado deja de ser una abstracción.
    """
    global nivel

    if estado["bomba"] == "encendida":
        nivel += random.uniform(2, 6)
    else:
        nivel -= random.uniform(1, 4)

    nivel = max(0.0, min(100.0, nivel))

    return {
        "nivel": round(nivel, 1),
        "temp": round(random.uniform(18, 36), 1),
        # La alarma se decide AQUÍ, en el dispositivo, con el umbral que le
        # bajó la nube. Es el patrón normal: la nube configura, el equipo
        # decide en tiempo real. Si se cae la conexión, sigue decidiendo.
        "alarma": nivel > estado["umbral"],
        # La marca de tiempo la pone el dispositivo, no la nube: si el
        # mensaje se retrasa, sigues sabiendo cuándo se midió.
        "ts": round(time.time(), 1),
    }


def transmitir(cliente: mqtt.Client) -> None:
    """Publica una lectura en el topic de telemetría.

    qos=0: "como mucho una vez". Para telemetría frecuente es lo normal —si
    se pierde una lectura, la siguiente viene en segundos y no pasa nada. El
    estado, en cambio, va con qos=1: ahí sí queremos confirmación.
    """
    muestra = medir()
    cliente.publish(config.TOPIC_TELEMETRIA, json.dumps(muestra), qos=0)

    marca = "  <- ALARMA" if muestra["alarma"] else ""
    print(f"  tx  nivel {muestra['nivel']:5.1f}   temp {muestra['temp']:4.1f}{marca}")


# ---------------------------------------------------------------------------
# La parte de estado (el shadow)
# ---------------------------------------------------------------------------


def aplicar(cambios: dict) -> None:
    """Hace caso a lo que pide el shadow.

    'cambios' es solo lo que hay que cambiar, no el estado completo: AWS
    manda únicamente los campos que difieren.
    """
    for clave, valor in cambios.items():
        if clave not in estado:
            # Un campo que no conocemos. En un equipo real esto pasa cuando
            # alguien actualiza la aplicación antes que el firmware. No es
            # motivo para caerse: lo ignoramos y seguimos funcionando.
            print(f"  (ignoro '{clave}': este equipo no sabe qué es)")
            continue

        anterior = estado[clave]
        estado[clave] = valor
        print(f"  {clave}: {anterior}  ->  {valor}")

        # AQUÍ iría la acción física de verdad: cerrar el relé de la bomba.
        # Primero se actúa, y solo si sale bien se reporta. Reportar algo
        # que no hiciste es la peor mentira que puede contar un dispositivo.


def reportar(cliente: mqtt.Client) -> None:
    """Le dice al shadow qué es este equipo ahora mismo.

    Fíjate en la envoltura: {"state": {"reported": {...}}}. Es obligatoria,
    y olvidarla es el error número uno con shadows.
    """
    mensaje = {"state": {"reported": estado}}
    cliente.publish(config.TOPIC_UPDATE, json.dumps(mensaje), qos=1)
    print(f"  reportado: {estado}")


def al_conectar(cliente, userdata, flags, codigo, propiedades=None):
    """Se ejecuta cuando AWS acepta la conexión. Aquí solo nos suscribimos.

    La regla de oro del shadow es «suscríbete a las respuestas antes de
    pedir nada». Pero hay una versión más fina, y es la que de verdad muerde:

        no basta con LLAMAR a subscribe(); hay que esperar a que AWS
        CONFIRME la suscripción.

    subscribe() solo deja la petición en camino. Si publicas tu /get justo
    después, es posible que AWS resuelva la consulta y mande la respuesta
    antes de haber terminado de registrar tu suscripción: la respuesta sale
    al topic, no hay nadie escuchando todavía, y se pierde. Tu programa se
    queda esperando para siempre, conectado y sin ningún error.

    Por eso el /get no se publica aquí, sino en al_suscribir().
    """
    global confirmadas

    print(f"Conectado a AWS como '{config.ID}'\n")
    confirmadas = 0

    for topic in config.TOPICS_DE_RESPUESTA:
        cliente.subscribe(topic, qos=1)


def al_suscribir(cliente, userdata, mid, codigos, propiedades=None):
    """AWS confirma una suscripción. Llega una vez por cada subscribe()."""
    global confirmadas

    confirmadas += 1
    if confirmadas < len(config.TOPICS_DE_RESPUESTA):
        return

    print("Preguntando por mi estado...")
    cliente.publish(config.TOPIC_GET, "", qos=1)


def arrancar_telemetria(cliente: mqtt.Client) -> None:
    """Deja claro que ya sabemos qué somos y empezamos a transmitir."""
    global listo

    if listo:
        return

    listo = True
    print(f"\nTransmitiendo en {config.TOPIC_TELEMETRIA} cada {estado['intervalo']} s.")
    print("Míralo llegar: IoT Core -> Probar -> Cliente de prueba de MQTT,")
    print("suscrito a  fablab/#\n")


def al_recibir(cliente, userdata, mensaje):
    """Reparte cada mensaje del shadow según el topic por el que llegó."""
    topic = mensaje.topic
    cuerpo = json.loads(mensaje.payload.decode() or "{}")

    # --- La respuesta a nuestro /get -------------------------------------
    if topic == config.TOPIC_GET_ACEPTADO:
        documento = cuerpo.get("state", {})

        # Si hay 'delta', mientras estábamos apagados alguien pidió algo que
        # todavía no hemos hecho. Eso es lo que vinimos a buscar.
        pendiente = documento.get("delta")

        if pendiente:
            print(f"\nHabía algo pendiente mientras estaba apagado: {pendiente}")
            aplicar(pendiente)
        else:
            print("Nada pendiente: mi estado ya coincide con el deseado.")

        reportar(cliente)
        arrancar_telemetria(cliente)

    # --- No existe todavía -----------------------------------------------
    elif topic == config.TOPIC_GET_RECHAZADO:
        if cuerpo.get("code") == 404:
            # Normal la primera vez: el shadow no se crea hasta que alguien
            # escribe en él. Lo creamos nosotros, reportando lo que somos.
            print("Todavía no tengo shadow. Lo creo con mi estado actual.")
            reportar(cliente)
            arrancar_telemetria(cliente)
        else:
            print(f"AWS rechazó mi consulta: {cuerpo}")

    # --- Una orden nueva, estando encendidos ------------------------------
    elif topic == config.TOPIC_DELTA:
        cambios = cuerpo.get("state", {})
        print(f"\nOrden recibida: {cambios}")
        aplicar(cambios)
        reportar(cliente)
        print()

    # --- AWS confirma que guardó lo que reportamos ------------------------
    elif topic == config.TOPIC_UPDATE_ACEPTADO:
        print(f"  (shadow guardado, versión {cuerpo.get('version')})")

    # --- AWS no lo guardó -------------------------------------------------
    elif topic == config.TOPIC_UPDATE_RECHAZADO:
        print(f"\n  AWS RECHAZÓ la actualización: {cuerpo}")
        print("  Un 400 suele ser JSON mal formado; un 409, que alguien")
        print("  escribió antes que tú y tu versión ya estaba vieja.\n")


def main() -> None:
    global ultimo_envio

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.ID)
    cliente.on_connect = al_conectar
    cliente.on_subscribe = al_suscribir
    cliente.on_message = al_recibir

    # La identidad del DISPOSITIVO: su certificado. Igual que en el 03.
    cliente.tls_set(
        ca_certs=RAIZ,
        certfile=CERTIFICADO,
        keyfile=LLAVE,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )
    cliente.connect(config.ENDPOINT, config.PUERTO, keepalive=30)

    # loop_start() atiende la red en segundo plano: recibe los deltas y
    # mantiene viva la conexión mientras nosotros seguimos con lo nuestro.
    # En el laboratorio 03, suscribir.py usaba loop_forever() porque no
    # tenía nada más que hacer. Este equipo sí: tiene que transmitir.
    cliente.loop_start()

    try:
        while True:
            # No transmitimos hasta saber qué estado debemos tener. Un equipo
            # que empieza a mandar datos antes de leer su configuración
            # transmite con valores que quizá ya no son los correctos.
            if listo and time.time() - ultimo_envio >= estado["intervalo"]:
                ultimo_envio = time.time()
                transmitir(cliente)

            # Dormimos poco para que un cambio de intervalo se note enseguida.
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\nApagado. (El shadow se queda en AWS con lo último que reporté.)")

    finally:
        cliente.loop_stop()
        cliente.disconnect()


if __name__ == "__main__":
    main()
