"""Laboratorio de protocolos IoT — servidor.

Dos cosas conviven aquí:

1. La API "didáctica" que consume el dispositivo simulado, escrita como la
   escribiría cualquiera: POST /telemetry, GET /config, POST /ack.
2. La maquinaria del laboratorio (/api/..., /ws) que alimenta la interfaz.

Si estás leyendo este archivo como alumno: la parte 1 es la que te interesa.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import espia
from .estado import estado
from .eventos import bus
from .inspector import reconstruir_http, reconstruir_respuesta_http

ESTATICOS = Path(__file__).resolve().parent.parent / "static"
CLAVE_DEMO = "demo-key"
DISPOSITIVO = os.getenv("DISPOSITIVO_ID", "tanque-03")
BASE_TOPIC = f"fablab/planta1/{DISPOSITIVO}"


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    espia.iniciar()
    reparto = asyncio.create_task(bus.repartir_siempre())
    try:
        yield
    finally:
        reparto.cancel()
        espia.detener()


aplicacion = FastAPI(
    title="Laboratorio de protocolos IoT",
    description=(
        "API de la clase 2. Pruébala desde aquí mismo: cada petición que hagas "
        "aparece en el inspector de la interfaz."
    ),
    lifespan=ciclo_de_vida,
)


def _inspeccionar(peticion: Request, cuerpo: bytes, codigo: int) -> dict:
    """Reconstruye la petición, la publica al inspector y devuelve el desglose."""
    ruta = peticion.url.path
    if peticion.url.query:
        ruta = f"{ruta}?{peticion.url.query}"
    desglose = reconstruir_http(
        peticion.method,
        ruta,
        peticion.scope["headers"],
        cuerpo,
    )
    bus.emitir(
        "paquete",
        protocolo="http",
        ruta=ruta,
        codigo=codigo,
        respuesta=reconstruir_respuesta_http(codigo, 0),
        **desglose,
    )
    return desglose


# =========================================================================
#  PARTE 1: la API que consume el dispositivo
# =========================================================================


@aplicacion.post("/telemetry")
async def recibir_telemetria(peticion: Request):
    """Recibe una muestra del sensor. Exige cabecera Authorization."""
    cuerpo = await peticion.body()

    # Retardo artificial, si el instructor lo activó.
    if estado.fallos["latencia_ms"]:
        await asyncio.sleep(estado.fallos["latencia_ms"] / 1000)

    codigo, respuesta = 201, {"ok": True}

    if peticion.headers.get("authorization") != f"Bearer {CLAVE_DEMO}":
        codigo, respuesta = 401, {"error": "credenciales inválidas"}
    else:
        try:
            datos = json.loads(cuerpo)
        except json.JSONDecodeError:
            datos = None
        if not isinstance(datos, dict) or "temp" not in datos:
            codigo, respuesta = 400, {"error": "falta el campo temp"}
        elif random.random() < estado.fallos["tasa_429"]:
            codigo, respuesta = 429, {"error": "demasiadas peticiones"}
        elif random.random() < estado.fallos["tasa_503"]:
            codigo, respuesta = 503, {"error": "servidor ocupado"}

    desglose = _inspeccionar(peticion, cuerpo, codigo)

    # Los bytes viajaron por la red aunque la respuesta sea un error: eso es
    # justamente lo que hace caro reintentar.
    estado.anotar_mensaje("http", desglose["bytes_total"], desglose["bytes_utiles"])
    if codigo >= 400:
        estado.anotar_error("http")

    return JSONResponse(respuesta, status_code=codigo)


@aplicacion.get("/config")
async def obtener_config(peticion: Request):
    """El dispositivo pregunta por su configuración. Esto es *polling*."""
    carga = dict(estado.config)
    if estado.comando_http:
        carga["cmd_id"] = estado.comando_http
    desglose = _inspeccionar(peticion, b"", 200)
    # No es telemetría: es el precio de preguntar. Se contabiliza aparte.
    estado.anotar_polling(desglose["bytes_total"])
    return JSONResponse(carga)


@aplicacion.post("/ack")
async def acusar_recibo(peticion: Request):
    """El dispositivo confirma que aplicó un comando. Mide la latencia."""
    cuerpo = await peticion.body()
    _inspeccionar(peticion, cuerpo, 200)
    try:
        cmd_id = json.loads(cuerpo).get("cmd_id")
    except json.JSONDecodeError:
        cmd_id = None
    resultado = estado.cerrar_comando(cmd_id) if cmd_id else None
    if resultado:
        bus.emitir("latencia", **resultado)
    return {"ok": bool(resultado)}


# =========================================================================
#  PARTE 2: maquinaria del laboratorio
# =========================================================================


@aplicacion.get("/sim/control")
async def control_del_simulador():
    """Lo consulta el simulador. No cuenta como tráfico del dispositivo."""
    return {
        "red_caida": estado.fallos["red_caida"],
        "intervalo_mqtt": estado.intervalo_mqtt,
    }


@aplicacion.post("/sim/evento")
async def evento_del_simulador(peticion: Request):
    """El simulador cuenta lo que le pasa: reintentos, cortes, colas."""
    datos = await peticion.json()
    if datos.get("reintento"):
        estado.anotar_reintento(datos.get("protocolo", "http"))
    bus.emitir(
        "aviso",
        nivel=datos.get("nivel", "info"),
        texto=datos.get("texto", ""),
        origen="dispositivo",
    )
    return {"ok": True}


@aplicacion.get("/api/estado")
async def estado_actual():
    return {
        "metricas": estado.resumen(),
        "config": estado.config,
        "intervalo_mqtt": estado.intervalo_mqtt,
        "fallos": estado.fallos,
        "topics": estado.topics,
        "dispositivo": DISPOSITIVO,
        "base_topic": BASE_TOPIC,
        "segundos_activo": round(time.time() - estado.inicio),
    }


@aplicacion.post("/api/comando")
async def enviar_comando(peticion: Request):
    """La interfaz manda un comando por una vía o por la otra."""
    datos = await peticion.json()
    via = datos.get("via", "mqtt")
    intervalo = float(datos.get("intervalo", 2))
    cmd_id = estado.registrar_comando(via, intervalo)

    if via == "mqtt":
        espia.publicar(
            f"{BASE_TOPIC}/comandos",
            json.dumps({"intervalo_s": intervalo, "cmd_id": cmd_id}),
            qos=1,
        )
        bus.emitir("aviso", nivel="info", texto=f"Comando publicado por MQTT (id {cmd_id})")
    else:
        bus.emitir(
            "aviso",
            nivel="info",
            texto=(
                f"Comando encolado en el servidor (id {cmd_id}). El dispositivo "
                f"se enterará en su próximo GET /config."
            ),
        )
    return {"cmd_id": cmd_id, "via": via}


@aplicacion.post("/api/fallos")
async def ajustar_fallos(peticion: Request):
    datos = await peticion.json()
    for clave in ("tasa_503", "tasa_429"):
        if clave in datos:
            estado.fallos[clave] = max(0.0, min(1.0, float(datos[clave])))
    if "latencia_ms" in datos:
        estado.fallos["latencia_ms"] = max(0, int(datos["latencia_ms"]))
    if "red_caida" in datos:
        estado.fallos["red_caida"] = bool(datos["red_caida"])
        bus.emitir(
            "aviso",
            nivel="error" if estado.fallos["red_caida"] else "ok",
            texto=(
                "Red del dispositivo CORTADA: el canal HTTP empezará a reintentar "
                "y el broker publicará el testamento del cliente MQTT."
                if estado.fallos["red_caida"]
                else "Red del dispositivo restablecida."
            ),
        )
    return estado.fallos


@aplicacion.post("/api/publicar")
async def publicar_a_mano(peticion: Request):
    """Para la pestaña de QoS: publicar en cualquier topic desde la interfaz."""
    datos = await peticion.json()
    espia.publicar(
        datos.get("topic", f"{BASE_TOPIC}/pruebas"),
        datos.get("carga", ""),
        qos=int(datos.get("qos", 0)),
        retener=bool(datos.get("retener", False)),
    )
    return {"ok": True}


@aplicacion.post("/api/reset")
async def reiniciar():
    estado.reiniciar_metricas()
    bus.emitir("reset")
    bus.emitir("aviso", nivel="ok", texto="Contadores en cero.")
    return {"ok": True}


@aplicacion.websocket("/ws")
async def canal_de_eventos(ws: WebSocket):
    await bus.conectar(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        bus.desconectar(ws)
    except Exception:
        bus.desconectar(ws)


# =========================================================================
#  Interfaz
# =========================================================================

aplicacion.mount("/static", StaticFiles(directory=ESTATICOS), name="static")


@aplicacion.get("/")
async def inicio():
    return FileResponse(ESTATICOS / "index.html")
