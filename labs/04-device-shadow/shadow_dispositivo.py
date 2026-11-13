"""El dispositivo: obedece al shadow y reporta lo que es.

QUÉ HACE
    Simula un equipo con dos cosas que se pueden controlar a distancia: una
    bomba (encendida/apagada) y un umbral de nivel. No publica telemetría:
    de eso se encargaba el laboratorio 03. Esto es otra cosa — aquí se
    gestiona ESTADO.

CÓMO SE EJECUTA
    docker compose run --rm dispositivo python shadow_dispositivo.py

    Para detenerlo: Ctrl + C   (y eso es, justamente, parte del laboratorio:
    apágalo, cámbiale el estado deseado desde la consola, y vuelve a
    encenderlo. Obedecerá.)

EL CICLO, QUE ES TODO LO QUE HAY QUE ENTENDER
    1. Me suscribo a las respuestas.      <- ANTES de pedir nada
    2. Pido el documento completo (/get). <- por si me perdí algo apagado
    3. Aplico lo que diga.
    4. Reporto lo que soy ahora.
    5. Me quedo escuchando deltas.

    El paso 2 es la diferencia entre este programa y el suscribir.py de la
    clase anterior. Aquel, al arrancar, no tenía forma de saber qué se había
    perdido mientras estuvo apagado. Este pregunta.

LAS TRES REGLAS DEL SHADOW
    - El dispositivo escribe 'reported'. Nunca 'desired'.
    - La aplicación escribe 'desired'. Nunca 'reported'.
    - El 'delta' no lo escribe nadie: lo calcula AWS.

    Este archivo solo escribe 'reported'. Busca la palabra 'desired' aquí
    dentro: no aparece en ningún publish. Esa disciplina es lo que hace que
    el estado de un sistema IoT sea razonable a las tres de la mañana.
"""

import json
import ssl

import paho.mqtt.client as mqtt

import config

# ---------------------------------------------------------------------------
# El estado del equipo, tal como lo conoce el propio equipo
# ---------------------------------------------------------------------------
# En un dispositivo de verdad esto sería el estado real del hardware: si el
# relé está cerrado, qué umbral tiene grabado en su memoria. Aquí es un
# diccionario, pero el papel que cumple es exactamente el mismo.

estado = {
    "bomba": "apagada",
    "umbral": 80,
}

# Cuántas de nuestras suscripciones ha confirmado AWS. Ver al_suscribir().
confirmadas = 0

# Comprobaciones previas: mejor un mensaje claro que un error de Python a
# mitad de la conexión.
rutas = config.identidad()
if not rutas:
    config.abandonar("Faltan los certificados. ¿Hiciste el laboratorio 03?")
if not config.ENDPOINT:
    config.abandonar("Falta tu endpoint. Revisa el .env del laboratorio 03.")

CERTIFICADO, LLAVE, RAIZ = rutas


def aplicar(cambios: dict) -> None:
    """Hace caso a lo que pide el shadow y luego lo reporta.

    'cambios' es solo lo que hay que cambiar, no el estado completo: AWS
    manda únicamente los campos que difieren. Si el umbral ya coincidía, el
    delta no lo incluye.
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

        # AQUÍ iría la acción física de verdad: cerrar el relé, mover la
        # válvula, grabar el umbral en la EEPROM. Primero se actúa, y solo
        # si sale bien se reporta. Reportar algo que no hiciste es la peor
        # mentira que puede contar un dispositivo.


def reportar(cliente: mqtt.Client) -> None:
    """Le dice al shadow qué es este equipo ahora mismo.

    Fíjate en la forma del mensaje: {"state": {"reported": {...}}}. Esa
    envoltura es obligatoria, y olvidarla es el error número uno con shadows.
    """
    mensaje = {"state": {"reported": estado}}
    cliente.publish(config.TOPIC_UPDATE, json.dumps(mensaje), qos=1)
    print(f"  reportado: {estado}")


def al_conectar(cliente, userdata, flags, codigo, propiedades=None):
    """Se ejecuta cuando AWS acepta la conexión. Aquí solo nos suscribimos.

    La regla de oro del shadow es «suscríbete a las respuestas antes de
    pedir nada». Pero hay una versión más fina de esa regla, y es la que de
    verdad muerde:

        no basta con LLAMAR a subscribe(); hay que esperar a que AWS
        CONFIRME la suscripción.

    subscribe() solo deja la petición en camino. Si publicas tu /get justo
    después, es perfectamente posible que AWS resuelva tu consulta y mande
    la respuesta antes de haber terminado de registrar tu suscripción: la
    respuesta sale al topic, no hay nadie escuchando todavía, y se pierde.

    Tu programa se queda esperando para siempre, conectado y sin ningún
    error. Por eso el /get no se publica aquí, sino en al_suscribir().
    """
    global confirmadas

    print(f"Conectado a AWS como '{config.ID}'\n")

    # En una reconexión esta función se vuelve a ejecutar, así que el
    # contador arranca de cero otra vez.
    confirmadas = 0

    for topic in config.TOPICS_DE_RESPUESTA:
        cliente.subscribe(topic, qos=1)


def al_suscribir(cliente, userdata, mid, codigos, propiedades=None):
    """AWS confirma una suscripción. Llega una vez por cada subscribe().

    Cuando están confirmadas las cinco, y solo entonces, preguntamos.
    """
    global confirmadas

    confirmadas += 1
    if confirmadas < len(config.TOPICS_DE_RESPUESTA):
        return

    # Ahora sí: "AWS, ¿qué debería ser yo?"
    print("Preguntando por mi estado...")
    cliente.publish(config.TOPIC_GET, "", qos=1)


def al_recibir(cliente, userdata, mensaje):
    """Reparte cada mensaje según el topic por el que llegó.

    Los cinco topics a los que estamos suscritos significan cosas distintas,
    así que lo primero es mirar de cuál viene.
    """
    topic = mensaje.topic
    cuerpo = json.loads(mensaje.payload.decode() or "{}")

    # --- La respuesta a nuestro /get -------------------------------------
    if topic == config.TOPIC_GET_ACEPTADO:
        documento = cuerpo.get("state", {})

        # Si hay 'delta', es que mientras estábamos apagados alguien pidió
        # algo que todavía no hemos hecho. Eso es exactamente lo que vinimos
        # a buscar.
        pendiente = documento.get("delta")

        if pendiente:
            print(f"\nHabía algo pendiente mientras estaba apagado: {pendiente}")
            aplicar(pendiente)
            reportar(cliente)
        else:
            print("Nada pendiente: mi estado ya coincide con el deseado.")
            # Reportamos igual, para que el shadow refleje la realidad desde
            # el primer segundo aunque nadie haya pedido nada.
            reportar(cliente)

        print("\nEsperando órdenes. Ctrl+C para salir.\n")

    # --- No existe todavía -----------------------------------------------
    elif topic == config.TOPIC_GET_RECHAZADO:
        if cuerpo.get("code") == 404:
            # Normal la primera vez: el shadow no se crea hasta que alguien
            # escribe en él. Lo creamos nosotros, reportando lo que somos.
            print("Todavía no tengo shadow. Lo creo ahora con mi estado actual.")
            reportar(cliente)
            print("\nEsperando órdenes. Ctrl+C para salir.\n")
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
        version = cuerpo.get("version")
        print(f"  (shadow guardado, versión {version})")

    # --- AWS no lo guardó -------------------------------------------------
    elif topic == config.TOPIC_UPDATE_RECHAZADO:
        print(f"\n  AWS RECHAZÓ la actualización: {cuerpo}")
        print("  Un 400 suele ser JSON mal formado; un 409, que alguien")
        print("  escribió antes que tú y tu versión ya estaba vieja.\n")


def main() -> None:
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.ID)
    cliente.on_connect = al_conectar
    cliente.on_subscribe = al_suscribir
    cliente.on_message = al_recibir

    # La identidad del DISPOSITIVO: su certificado. Idéntico al laboratorio
    # 03; lo único que cambia en todo este archivo son los topics.
    cliente.tls_set(
        ca_certs=RAIZ,
        certfile=CERTIFICADO,
        keyfile=LLAVE,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )
    cliente.connect(config.ENDPOINT, config.PUERTO, keepalive=30)

    try:
        cliente.loop_forever()
    except KeyboardInterrupt:
        print("\nApagado. (El shadow se queda en AWS con lo último que reporté.)")
        cliente.disconnect()


if __name__ == "__main__":
    main()
