# =====================================================================
#  El modelo de la arquitectura
# =====================================================================
#
#  Un sitio y solo uno donde está escrito qué cajas hay, cómo se unen y
#  qué significa cada una. La página no sabe nada: lo pide y lo dibuja.
#
#  Cada nodo apunta a los recursos de infra/laboratorio.yaml que lo
#  crean. De ahí sale la pestaña "cómo lo creamos": el YAML de verdad,
#  con sus comentarios, no un ejemplo.
# =====================================================================

import os
import re

PLANTILLA = os.environ.get("PLANTILLA", "/plantilla/laboratorio.yaml")


# ---------------------------------------------------------------------
#  Las cajas
# ---------------------------------------------------------------------
#  x, y, w, h están en el mismo sistema que el viewBox del SVG
#  (1200 x 640). Las coordenadas viven aquí y no en el JavaScript para
#  que mover una caja sea tocar un archivo, no dos.
# ---------------------------------------------------------------------

NODOS = [
    {
        "id": "dispositivo",
        "titulo": "Tu dispositivo",
        "servicio": "Contenedor en tu laptop",
        "clase": 3,
        "x": 24, "y": 150, "w": 158, "h": 74,
        "familia": "tuyo",
        "que_es": (
            "Un programa Python corriendo en Docker que simula un sensor de "
            "nivel. No es AWS: es tuyo, y por eso está en rojo en el dibujo."
        ),
        "como_lo_usamos": (
            "Publica un mensaje JSON cada diez segundos en el topic "
            "fablab/planta1/<tu-equipo>/telemetria, firmado con su "
            "certificado X.509. Desde la clase 4 además obedece a su shadow."
        ),
        "coste": "Gratis: corre en tu máquina.",
        "recursos": [],
    },
    {
        "id": "iotcore",
        "titulo": "AWS IoT Core",
        "servicio": "AWS::IoT::Thing · AWS::IoT::Policy",
        "clase": 3,
        "x": 236, "y": 150, "w": 168, "h": 74,
        "familia": "aws",
        "que_es": (
            "La puerta de entrada. Un broker MQTT gestionado que autentica "
            "cada dispositivo por su certificado y decide, con una política, "
            "qué topics puede tocar."
        ),
        "como_lo_usamos": (
            "Recibe la telemetría y la pone a disposición de las reglas. "
            "La política usa ${iot:Connection.Thing.ThingName}, así que cada "
            "equipo solo puede publicar en SU topic aunque todos compartan "
            "la plantilla."
        ),
        "coste": "Free Tier: 2,25 M de mensajes al mes durante 12 meses.",
        "recursos": ["Objeto", "PoliticaDispositivo"],
    },
    {
        "id": "regla_guardar",
        "titulo": "Regla: guardar",
        "servicio": "AWS::IoT::TopicRule",
        "clase": 6,
        "x": 456, "y": 44, "w": 172, "h": 74,
        "familia": "regla",
        "que_es": (
            "Una consulta SQL que mira todos los mensajes que pasan por el "
            "broker y, con los que encajan, hace algo. Esta no filtra nada."
        ),
        "como_lo_usamos": (
            "SELECT * sin WHERE: guardar todo es el trabajo. Añade dos campos "
            "que el mensaje no traía, topic(3) y parse_time(...), que son "
            "justamente las dos claves de la tabla. Tiene DOS acciones: "
            "escribe en DynamoDB y en S3 con el mismo disparo."
        ),
        "coste": "Free Tier: 250 000 activaciones de regla al mes.",
        "recursos": ["ReglaGuardar", "RolReglaGuardar"],
    },
    {
        "id": "regla_alarmas",
        "titulo": "Regla: alarmas",
        "servicio": "AWS::IoT::TopicRule",
        "clase": 5,
        "x": 456, "y": 180, "w": 172, "h": 74,
        "familia": "regla",
        "que_es": (
            "La misma clase de recurso que la de arriba, pero con WHERE. "
            "Dos reglas miran los mismos mensajes sin estorbarse."
        ),
        "como_lo_usamos": (
            "WHERE alarma = true. Solo cuando el nivel pasa del umbral "
            "invoca a la Lambda. Se filtra lo que se AVISA, no lo que se "
            "guarda: avisar de todo es ruido."
        ),
        "coste": "Dentro de las mismas 250 000 activaciones.",
        "recursos": ["ReglaAlarmas", "RolReglaAlarmas"],
    },
    {
        "id": "regla_metrica",
        "titulo": "Regla: métrica",
        "servicio": "AWS::IoT::TopicRule",
        "clase": 7,
        "x": 456, "y": 316, "w": 172, "h": 74,
        "familia": "regla",
        "que_es": (
            "La tercera regla. Su acción no escribe ni invoca nada: publica "
            "una métrica."
        ),
        "como_lo_usamos": (
            "Convierte el campo nivel en una métrica de CloudWatch, una por "
            "equipo. Es el contraste de la clase 7: el panel lo construyes "
            "tú, esta curva ya venía hecha."
        ),
        "coste": "Free Tier: 10 métricas personalizadas, para siempre.",
        "recursos": ["ReglaMetrica", "RolMetrica"],
    },
    {
        "id": "dynamodb",
        "titulo": "DynamoDB",
        "servicio": "AWS::DynamoDB::Table",
        "clase": 6,
        "x": 696, "y": 20, "w": 158, "h": 74,
        "familia": "almacen",
        "que_es": (
            "Una base de datos de clave-valor. Responde en milisegundos si "
            "preguntas por la clave, y no sabe responder a casi nada más."
        ),
        "como_lo_usamos": (
            "El 'cómo está ahora'. Clave de partición dispositivo (DE QUIÉN) "
            "y clave de ordenación momento (CUÁNDO). Solo las claves se "
            "declaran: nivel, temp y lo que venga aparecen solos."
        ),
        "coste": "Free Tier permanente: 25 unidades de lectura y 25 de escritura, "
                 "solo en modo aprovisionado. Bajo demanda se paga desde la primera fila.",
        "recursos": ["Tabla"],
    },
    {
        "id": "s3",
        "titulo": "S3",
        "servicio": "AWS::S3::Bucket",
        "clase": 6,
        "x": 696, "y": 118, "w": 158, "h": 74,
        "familia": "almacen",
        "que_es": (
            "Un almacén de archivos. Solo sabe listar nombres y entregar "
            "archivos: no puede buscar dentro."
        ),
        "como_lo_usamos": (
            "El 'qué pasó'. Un archivo JSON por mensaje, en carpetas "
            "<equipo>/<año>/<mes>/<día>/. Diez veces más barato por gigabyte "
            "que DynamoDB, y por eso aquí va el histórico."
        ),
        "coste": "Free Tier: 5 GB y 2000 PUT al mes, durante 12 meses.",
        "recursos": ["Bucket"],
    },
    {
        "id": "lambda_alarma",
        "titulo": "Lambda: avisar",
        "servicio": "AWS::Lambda::Function",
        "clase": 5,
        "x": 696, "y": 180, "w": 158, "h": 74,
        "familia": "codigo",
        "que_es": (
            "Código que corre cuando alguien lo llama, sin servidor que "
            "mantener. Se paga por invocación y por milisegundo."
        ),
        "como_lo_usamos": (
            "Decide el texto del aviso y lo publica en SNS. Ojo con el estado "
            "global: el contenedor se reutiliza entre invocaciones, así que "
            "una variable que creas tuya puede sobrevivir — o desaparecer."
        ),
        "coste": "Free Tier permanente: 1 millón de invocaciones al mes.",
        "recursos": ["Funcion", "RolFuncion", "PermisoDeInvocacion"],
    },
    {
        "id": "sns",
        "titulo": "SNS → tu correo",
        "servicio": "AWS::SNS::Topic · Subscription",
        "clase": 5,
        "x": 930, "y": 180, "w": 158, "h": 74,
        "familia": "aviso",
        "que_es": (
            "Un servicio de notificaciones. Publicas en un tema y él reparte "
            "a todos los suscritos: correo, SMS, otra Lambda…"
        ),
        "como_lo_usamos": (
            "Un tema estándar con tu correo suscrito. Tienes que confirmar la "
            "suscripción desde el buzón: hasta entonces no llega nada. Los "
            "temas FIFO no admiten correo, por eso este es estándar."
        ),
        "coste": "Free Tier permanente: 1000 correos al mes.",
        "recursos": ["TemaAlarmas", "SuscripcionCorreo"],
    },
    {
        "id": "cloudwatch",
        "titulo": "CloudWatch",
        "servicio": "Métricas y registros",
        "clase": 7,
        "x": 696, "y": 316, "w": 158, "h": 74,
        "familia": "aviso",
        "que_es": (
            "Donde AWS deja los registros y las métricas de todo lo demás. "
            "Si una Lambda falla, el motivo está aquí."
        ),
        "como_lo_usamos": (
            "Recibe la métrica del nivel en el espacio FabLab/Tanques, una "
            "serie por equipo. Es la curva que no hubo que programar."
        ),
        "coste": "Free Tier permanente: 10 métricas, 10 alarmas y 3 paneles.",
        "recursos": [],
    },
    {
        "id": "api",
        "titulo": "Lambda: la API",
        "servicio": "AWS::Lambda::Function · Url",
        "clase": 7,
        "x": 456, "y": 470, "w": 172, "h": 74,
        "familia": "codigo",
        "que_es": (
            "Otra función, pero con una dirección HTTPS propia: una Function "
            "URL, sin API Gateway de por medio."
        ),
        "como_lo_usamos": (
            "Recibe la pregunta, busca en DynamoDB o en S3 y contesta JSON. "
            "Su rol es de SOLO LECTURA. La URL va con AuthType NONE: cualquiera "
            "que la tenga puede preguntar, y por eso la pila se borra al acabar."
        ),
        "coste": "Dentro del mismo millón de invocaciones.",
        "recursos": ["Api", "RolApi", "UrlApi", "PermisoUrl", "PermisoInvocarApi"],
    },
    {
        "id": "navegador",
        "titulo": "Tu navegador",
        "servicio": "El panel, en tu laptop",
        "clase": 7,
        "x": 24, "y": 470, "w": 158, "h": 74,
        "familia": "tuyo",
        "que_es": (
            "Una página estática. No sabe nada de AWS y no tiene credenciales."
        ),
        "como_lo_usamos": (
            "Arma una dirección con lo que quieres preguntar, la pide y pinta "
            "lo que vuelve. Quien tiene los permisos es la Lambda, al otro lado."
        ),
        "coste": "Gratis.",
        "recursos": [],
    },
]


# ---------------------------------------------------------------------
#  Las flechas
# ---------------------------------------------------------------------
#  "autoriza" es lo que hace posible esa flecha. Es la capa que se
#  enciende con el interruptor de permisos, y la que más cuesta ver:
#  en el dibujo normal una flecha parece que existe porque sí.
#
#  "rama" agrupa las flechas que se encienden juntas cuando llega un
#  mensaje de verdad.
# ---------------------------------------------------------------------

ARISTAS = [
    {"de": "dispositivo", "a": "iotcore", "etiqueta": "MQTT/TLS",
     "autoriza": "Certificado X.509 del dispositivo", "rama": "entrada"},

    {"de": "iotcore", "a": "regla_guardar", "etiqueta": "SELECT *",
     "autoriza": "La regla vive dentro de IoT Core", "rama": "guardar"},
    {"de": "iotcore", "a": "regla_alarmas", "etiqueta": "WHERE alarma",
     "autoriza": "La regla vive dentro de IoT Core", "rama": "alarma"},
    {"de": "iotcore", "a": "regla_metrica", "etiqueta": "SELECT *",
     "autoriza": "La regla vive dentro de IoT Core", "rama": "metrica"},

    {"de": "regla_guardar", "a": "dynamodb", "etiqueta": "PutItem",
     "autoriza": "Rol de IAM de la regla (dynamodb:PutItem)", "rama": "guardar"},
    {"de": "regla_guardar", "a": "s3", "etiqueta": "PutObject",
     "autoriza": "Rol de IAM de la regla (s3:PutObject)", "rama": "guardar"},

    {"de": "regla_alarmas", "a": "lambda_alarma", "etiqueta": "invoca",
     "autoriza": "Rol de la regla + política de recurso de la Lambda", "rama": "alarma"},
    {"de": "lambda_alarma", "a": "sns", "etiqueta": "Publish",
     "autoriza": "Rol de IAM de la función (sns:Publish)", "rama": "alarma"},

    {"de": "regla_metrica", "a": "cloudwatch", "etiqueta": "PutMetricData",
     "autoriza": "Rol de IAM de la regla (cloudwatch:PutMetricData)", "rama": "metrica"},

    {"de": "navegador", "a": "api", "etiqueta": "HTTPS",
     "autoriza": "Nadie: AuthType NONE. La URL es pública", "rama": "consulta"},
    {"de": "api", "a": "dynamodb", "etiqueta": "Query",
     "autoriza": "Rol de IAM de la API (solo lectura)", "rama": "consulta"},
    {"de": "api", "a": "s3", "etiqueta": "GetObject",
     "autoriza": "Rol de IAM de la API (solo lectura)", "rama": "consulta"},
]


# ---------------------------------------------------------------------
#  Qué se rompe si quitas una caja
# ---------------------------------------------------------------------
#  Esto está escrito a mano, nodo por nodo, y no deducido del grafo a
#  propósito. Un algoritmo genérico "todo lo que cuelga de aquí se cae"
#  se equivoca justo en los casos que más enseñan:
#
#    · Si quitas DynamoDB, la regla de guardar NO se cae entera: su otra
#      acción sigue escribiendo en S3. Una regla con dos acciones falla
#      a medias, y eso hay que decirlo.
#    · Si quitas S3, la API sigue respondiendo a "cómo está ahora" y
#      solo falla la pregunta del día completo.
#    · Si quitas la regla de alarmas, no se cae nada: simplemente deja
#      de avisar. El sistema sigue guardando y nadie se entera.
#
#  "grave" marca lo que deja de funcionar; sin él, lo que solo se queda
#  sin datos nuevos.
# ---------------------------------------------------------------------

SI_FALTA = {
    "dispositivo": [
        ("iotcore", "no entra nada: el broker se queda sin tráfico", False),
        ("regla_guardar", "no se activa nunca", False),
        ("regla_alarmas", "no se activa nunca", False),
        ("regla_metrica", "no se activa nunca", False),
        ("dynamodb", "deja de crecer; lo guardado sigue ahí", False),
        ("s3", "deja de crecer; lo guardado sigue ahí", False),
        ("cloudwatch", "la curva se queda plana", False),
        ("sns", "no llega ningún aviso", False),
        ("api", "sigue en pie y contesta, pero solo lo viejo", False),
    ],
    "iotcore": [
        ("regla_guardar", "las reglas viven dentro: desaparecen con él", True),
        ("regla_alarmas", "las reglas viven dentro: desaparecen con él", True),
        ("regla_metrica", "las reglas viven dentro: desaparecen con él", True),
        ("dispositivo", "no tiene dónde publicar; se queda reintentando", True),
        ("dynamodb", "deja de recibir", False),
        ("s3", "deja de recibir", False),
        ("sns", "no llega ningún aviso", False),
        ("cloudwatch", "sin métrica", False),
    ],
    "regla_guardar": [
        ("dynamodb", "deja de recibir filas", False),
        ("s3", "deja de recibir archivos", False),
        ("api", "contestará listas vacías: no hay nada nuevo que leer", False),
    ],
    "regla_alarmas": [
        ("lambda_alarma", "no se invoca nunca", True),
        ("sns", "no se publica nada", True),
    ],
    "regla_metrica": [
        ("cloudwatch", "sin métrica que dibujar", True),
    ],
    "dynamodb": [
        ("regla_guardar", "su acción de DynamoDB falla; la de S3 sigue escribiendo", False),
        ("api", "la pregunta «cómo está ahora» falla; el día completo sigue", False),
    ],
    "s3": [
        ("regla_guardar", "su acción de S3 falla; la de DynamoDB sigue escribiendo", False),
        ("api", "la pregunta del día completo falla; las últimas lecturas siguen", False),
    ],
    "lambda_alarma": [
        ("sns", "nadie publica en el tema", True),
    ],
    "sns": [],
    "cloudwatch": [],
    "api": [
        ("navegador", "el panel no tiene a quién preguntar", True),
    ],
    "navegador": [],
}


def si_falta(nodo_id):
    return [{"nodo": n, "efecto": e, "grave": g}
            for n, e, g in SI_FALTA.get(nodo_id, [])]


# ---------------------------------------------------------------------
#  Sacar un recurso de la plantilla, con sus comentarios
# ---------------------------------------------------------------------
#  A propósito NO se usa un analizador de YAML: PyYAML devolvería la
#  estructura y tiraría los comentarios, que es justo lo que queremos
#  enseñar. Se recorta por indentación, como lo haría una persona.
# ---------------------------------------------------------------------

def bloque_de(texto, logico):
    lineas = texto.split("\n")

    cabecera = None
    for i, l in enumerate(lineas):
        if re.match(r"^  " + re.escape(logico) + r":\s*$", l):
            cabecera = i
            break
    if cabecera is None:
        return None

    # Sube por los comentarios pegados encima: explican por qué existe el
    # recurso, y sin ellos el bloque pierde la mitad de su valor.
    inicio = cabecera
    while inicio > 0 and lineas[inicio - 1].lstrip().startswith("#"):
        inicio -= 1

    # Baja hasta la siguiente línea de primer nivel (dos espacios o menos),
    # que ya es otro recurso o el final de la sección.
    fin = len(lineas)
    for i in range(cabecera + 1, len(lineas)):
        l = lineas[i]
        if l.strip() == "":
            continue
        if len(l) - len(l.lstrip()) <= 2:
            fin = i
            break

    # Los comentarios del final son la cabecera del recurso siguiente.
    recorte = lineas[inicio:fin]
    while recorte and (recorte[-1].strip() == "" or recorte[-1].lstrip().startswith("#")):
        recorte.pop()
    return "\n".join(recorte)


def yaml_de(nodo_id):
    """Todos los bloques de la plantilla que crean ese nodo."""
    nodo = next((n for n in NODOS if n["id"] == nodo_id), None)
    if nodo is None:
        return []
    if not nodo["recursos"]:
        return []
    try:
        with open(PLANTILLA, encoding="utf-8") as f:
            texto = f.read()
    except OSError:
        return []
    salida = []
    for logico in nodo["recursos"]:
        bloque = bloque_de(texto, logico)
        if bloque:
            salida.append({"logico": logico, "yaml": bloque})
    return salida


def para_la_pagina():
    """Lo que la página necesita para dibujar, sin el YAML (va aparte)."""
    return {
        "nodos": [dict(n, si_falta=si_falta(n["id"])) for n in NODOS],
        "aristas": ARISTAS,
        # El alto va justo por debajo de la caja más baja (544) más un
        # respiro para las etiquetas que cuelgan encima de los nodos.
        "lienzo": {"w": 1200, "h": 568},
    }
