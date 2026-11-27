# =====================================================================
#  La plataforma  ·  servidor
# =====================================================================
#
#  Tres cosas y nada más:
#
#    1. Sirve la página (archivos estáticos de /srv/web).
#    2. Lee TU cuenta de AWS, SOLO LECTURA, con el perfil que le montes.
#    3. Empuja por SSE cada fila nueva que aparece en la tabla, para que
#       el diagrama se encienda cuando tu dispositivo publica.
#
#  Las credenciales NO bajan nunca al navegador: la página le pregunta a
#  este servidor, y este servidor habla con AWS. Es el mismo reparto que
#  la Lambda de la clase 7, pero en tu laptop.
#
#  Si no hay cuenta, o la pila no está desplegada, arranca en MODO
#  DEMOSTRACIÓN con datos inventados: el día que falle el wifi del aula
#  la clase sigue.
# =====================================================================

import json
import os
import queue
import threading
import time
from decimal import Decimal
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import arquitectura

NOMBRE = os.environ.get("NOMBRE_OBJETO", "demo-clase3")
REGION = os.environ.get("AWS_REGION", "us-east-2")
WEB = "/srv/web"
PUERTO = 80

TABLA = f"{NOMBRE}-telemetria"

# Estado compartido entre el hilo que vigila y las conexiones SSE.
_suscriptores = []
_candado = threading.Lock()
# La última fila vista, para poder contársela a quien abra la página
# ahora. Sin esto, una pestaña recién abierta con el dispositivo parado
# se queda en "esperando" para siempre y parece que la herramienta está
# rota, cuando lo que está parado es el equipo.
_ultimo = {"evento": None}
_modo = {"demo": False, "motivo": "", "cuenta": "", "bucket": ""}
_estado = {"datos": None, "cuando": 0}


# ---------------------------------------------------------------------
#  AWS, solo lectura
# ---------------------------------------------------------------------

def sesion():
    import boto3
    perfil = os.environ.get("AWS_PROFILE")
    if perfil:
        return boto3.Session(profile_name=perfil, region_name=REGION)
    return boto3.Session(region_name=REGION)


def arrancar_aws():
    """Decide si hay cuenta utilizable. No lanza: degrada a demostración."""
    try:
        s = sesion()
        cuenta = s.client("sts").get_caller_identity()["Account"]
        _modo["cuenta"] = cuenta
        _modo["bucket"] = f"{NOMBRE}-telemetria-{cuenta}"
        s.client("dynamodb").describe_table(TableName=TABLA)
        _modo["demo"] = False
        return s
    except Exception as e:
        _modo["demo"] = True
        _modo["motivo"] = f"{type(e).__name__}: {e}"
        return None


def limpiar(x):
    if isinstance(x, list):
        return [limpiar(i) for i in x]
    if isinstance(x, dict):
        return {k: limpiar(v) for k, v in x.items()}
    if isinstance(x, Decimal):
        return float(x)
    return x


def filas(s, n=50, desde=None, hasta=None, ascendente=False):
    from boto3.dynamodb.conditions import Key
    tabla = s.resource("dynamodb").Table(TABLA)
    cond = Key("dispositivo").eq(NOMBRE)
    if desde and hasta:
        cond = cond & Key("momento").between(desde, hasta)
    r = tabla.query(KeyConditionExpression=cond,
                    ScanIndexForward=ascendente, Limit=n)
    return limpiar(r["Items"])


# ---------------------------------------------------------------------
#  El vigía
# ---------------------------------------------------------------------
#  Pregunta por la fila más reciente cada dos segundos. Cuando aparece
#  una nueva, la reparte a todas las pestañas abiertas.
#
#  No espía el broker: mira lo que LLEGÓ a la tabla. Es una diferencia
#  importante y la página la dice. Cada fila es la prueba de que la
#  cadena entera funcionó — dispositivo, broker, regla y escritura.
# ---------------------------------------------------------------------

def ramas_de(fila):
    ramas = ["entrada", "guardar"]
    if fila.get("alarma") is True:
        ramas.append("alarma")
    ramas.append("metrica")
    return ramas


def repartir(evento):
    if evento.get("tipo") == "fila":
        _ultimo["evento"] = evento
    with _candado:
        muertos = []
        for q in _suscriptores:
            try:
                q.put_nowait(evento)
            except Exception:
                muertos.append(q)
        for q in muertos:
            _suscriptores.remove(q)


def vigia():
    s = arrancar_aws()
    ultimo = None

    if _modo["demo"]:
        import random
        while True:
            nivel = round(random.uniform(5, 100), 1)
            fila = {"dispositivo": NOMBRE, "momento": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                    "nivel": nivel, "temp": round(random.uniform(18, 35), 1),
                    "alarma": nivel > 90}
            repartir({"tipo": "fila", "fila": fila, "ramas": ramas_de(fila), "demo": True})
            time.sleep(4)

    # La primera lectura no es tráfico nuevo: es el estado de partida.
    # Se guarda sin encender ramas, para no fingir un mensaje que no
    # acaba de pasar.
    try:
        f = filas(s, n=1)
        if f:
            ultimo = f[0].get("momento")
            _ultimo["evento"] = {"tipo": "fila", "fila": f[0], "ramas": [],
                                 "historico": True}
    except Exception:
        pass

    while True:
        try:
            f = filas(s, n=1)
            if f and f[0].get("momento") != ultimo:
                ultimo = f[0].get("momento")
                repartir({"tipo": "fila", "fila": f[0], "ramas": ramas_de(f[0]), "demo": False})
        except Exception as e:
            repartir({"tipo": "fallo", "error": f"{type(e).__name__}: {e}"})
        time.sleep(2)


# ---------------------------------------------------------------------
#  Qué hay de verdad en la cuenta
# ---------------------------------------------------------------------
#  La tercera pestaña de cada servicio, y la herramienta de soporte: al
#  alumno que dice "a mí no me funciona" se le abre esto y se ve en qué
#  eslabón se rompió.
# ---------------------------------------------------------------------

#  Un "✕ IndexError" no le enseña nada a nadie. Lo que el alumno
#  necesita saber es QUÉ nombre se esperaba y por qué no apareció —
#  casi siempre porque ese recurso lo creó a mano, en la consola, con
#  otro nombre. Eso es deriva, y verla es media clase de la 8.
NO_ESTA = ("ResourceNotFoundException", "UnauthorizedException",
           "NoSuchEntity", "IndexError", "StopIteration", "NotFoundException")
SIN_PERMISO = ("AccessDeniedException", "AccessDenied", "ClientError")


def mirar(fn, esperaba=None):
    try:
        return {"ok": True, "detalle": fn()}
    except Exception as e:
        nombre = type(e).__name__
        if nombre in NO_ESTA:
            d = f"no existe «{esperaba}»" if esperaba else "no existe"
            return {"ok": False, "detalle": d, "porque": "ausente"}
        if nombre in SIN_PERMISO:
            return {"ok": False, "detalle": "tu usuario no tiene permiso para consultarlo",
                    "porque": "permiso"}
        return {"ok": False, "detalle": f"{nombre}: {e}"[:160], "porque": "otro"}


def estado_real():
    if _modo["demo"]:
        return {"demo": True, "motivo": _modo["motivo"], "nodos": {}}

    s = sesion()
    iot = s.client("iot")
    r = {"demo": False, "cuenta": _modo["cuenta"], "nodos": {}}

    def regla(nombre):
        def _():
            d = iot.get_topic_rule(ruleName=nombre)["rule"]
            return ("activa" if not d.get("ruleDisabled") else "DESACTIVADA") + \
                   f" · {len(d.get('actions', []))} acción(es)"
        return _

    sub = NOMBRE.replace("-", "_")

    r["nodos"]["iotcore"] = mirar(
        lambda: iot.describe_thing(thingName=NOMBRE)["thingName"], NOMBRE)
    r["nodos"]["regla_guardar"] = mirar(regla(f"{sub}_guardar"), f"{sub}_guardar")
    r["nodos"]["regla_alarmas"] = mirar(regla(f"{sub}_alarmas"), f"{sub}_alarmas")
    r["nodos"]["regla_metrica"] = mirar(regla(f"{sub}_metricas"), f"{sub}_metricas")

    def tabla():
        d = s.client("dynamodb").describe_table(TableName=TABLA)["Table"]
        return f"{d['ItemCount']} fila(s) · {d['TableStatus']}"
    r["nodos"]["dynamodb"] = mirar(tabla, TABLA)

    def bucket():
        o = s.client("s3").list_objects_v2(Bucket=_modo["bucket"], MaxKeys=1000)
        return f"{o.get('KeyCount', 0)} archivo(s)"
    r["nodos"]["s3"] = mirar(bucket, _modo["bucket"])

    def fn(nombre):
        def _():
            d = s.client("lambda").get_function_configuration(FunctionName=nombre)
            return f"{d['Runtime']} · {d['State']}"
        return _
    r["nodos"]["lambda_alarma"] = mirar(fn(f"{NOMBRE}-alarma"), f"{NOMBRE}-alarma")
    r["nodos"]["api"] = mirar(fn(f"{NOMBRE}-api"), f"{NOMBRE}-api")

    def tema():
        sns = s.client("sns")
        arn = [t["TopicArn"] for t in sns.list_topics()["Topics"]
               if t["TopicArn"].endswith(f":{NOMBRE}-alarmas")][0]
        subs = sns.list_subscriptions_by_topic(TopicArn=arn)["Subscriptions"]
        conf = [x for x in subs if x["SubscriptionArn"] != "PendingConfirmation"]
        return f"{len(conf)} de {len(subs)} suscripción(es) confirmada(s)"
    r["nodos"]["sns"] = mirar(tema, f"{NOMBRE}-alarmas")

    def metricas():
        cw = s.client("cloudwatch")
        m = cw.list_metrics(Namespace="FabLab/Tanques")["Metrics"]
        return f"{len(m)} métrica(s) en FabLab/Tanques"
    r["nodos"]["cloudwatch"] = mirar(metricas)

    return r


# ---------------------------------------------------------------------
#  HTTP
# ---------------------------------------------------------------------

class Manejador(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def log_message(self, *a):
        pass

    def _json(self, datos, codigo=200):
        cuerpo = json.dumps(datos).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        param = {}
        if "?" in self.path:
            from urllib.parse import parse_qs
            param = {k: v[0] for k, v in parse_qs(self.path.split("?", 1)[1]).items()}

        if ruta == "/api/arquitectura":
            d = arquitectura.para_la_pagina()
            d["equipo"] = NOMBRE
            d["demo"] = _modo["demo"]
            d["motivo"] = _modo["motivo"]
            return self._json(d)

        if ruta == "/api/yaml":
            return self._json({"bloques": arquitectura.yaml_de(param.get("nodo", ""))})

        if ruta == "/api/estado":
            ahora = time.time()
            if _estado["datos"] is None or ahora - _estado["cuando"] > 30:
                try:
                    _estado["datos"] = estado_real()
                except Exception as e:
                    _estado["datos"] = {"error": f"{type(e).__name__}: {e}", "nodos": {}}
                _estado["cuando"] = ahora
            return self._json(_estado["datos"])

        if ruta == "/api/datos":
            return self._datos(param)

        if ruta == "/api/eventos":
            return self._eventos()

        return super().do_GET()

    def _datos(self, p):
        if _modo["demo"]:
            return self._json({"demo": True, "filas": []})
        try:
            s = sesion()
            accion = p.get("accion", "ultimas")
            n = int(p.get("n", 50))
            if accion == "rango":
                f = filas(s, n=n, desde=p.get("desde"), hasta=p.get("hasta"),
                          ascendente=True)
            else:
                f = filas(s, n=n)
            cuerpo = {"filas": f}
            if accion == "resumen":
                umbral = float(p.get("umbral", 90))
                niveles = [x["nivel"] for x in f if "nivel" in x]
                cuerpo["resumen"] = ({
                    "cuantas": len(f), "maximo": max(niveles), "minimo": min(niveles),
                    "media": round(sum(niveles) / len(niveles), 2),
                    "sobre_umbral": len([x for x in niveles if x > umbral]),
                    "umbral": umbral,
                } if niveles else {"cuantas": 0})
            return self._json(cuerpo)
        except Exception as e:
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def _eventos(self):
        q = queue.Queue(maxsize=50)
        with _candado:
            _suscriptores.append(q)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            if _ultimo["evento"]:
                self.wfile.write(
                    f"data: {json.dumps(_ultimo['evento'])}\n\n".encode())
                self.wfile.flush()
            while True:
                try:
                    ev = q.get(timeout=15)
                    self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": latido\n\n")   # mantiene viva la conexión
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with _candado:
                if q in _suscriptores:
                    _suscriptores.remove(q)


if __name__ == "__main__":
    threading.Thread(target=vigia, daemon=True).start()
    print(f"Plataforma en marcha · equipo {NOMBRE} · región {REGION}", flush=True)
    ThreadingHTTPServer(("", PUERTO), Manejador).serve_forever()
