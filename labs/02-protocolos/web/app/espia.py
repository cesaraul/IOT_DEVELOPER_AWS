"""Cliente MQTT del servidor: espía y publicador de comandos.

Se suscribe a '#' (todo lo que pasa por el broker) para alimentar el inspector
y el explorador de topics. Es, literalmente, un suscriptor más: el navegador
podría hacer exactamente lo mismo y de hecho lo hace en la pestaña de topics.
"""

from __future__ import annotations

import json
import os

import paho.mqtt.client as mqtt

from .estado import estado
from .eventos import bus
from .inspector import desglosar_mqtt

HOST = os.getenv("MQTT_HOST", "localhost")
PUERTO = int(os.getenv("MQTT_PORT", "1883"))

_cliente: mqtt.Client | None = None


def _al_conectar(cliente, userdata, flags, codigo, propiedades=None):
    cliente.subscribe("#", qos=0)
    bus.emitir("aviso", nivel="ok", texto=f"Espía MQTT conectado al broker ({codigo})")


def _al_desconectar(cliente, userdata, flags, codigo, propiedades=None):
    bus.emitir("aviso", nivel="error", texto=f"Espía MQTT desconectado ({codigo})")


def _al_recibir(cliente, userdata, mensaje: mqtt.MQTTMessage):
    topic = mensaje.topic
    carga = mensaje.payload
    texto = carga.decode("utf-8", "replace")

    desglose = desglosar_mqtt(topic, carga, mensaje.qos)
    estado.anotar_topic(topic, texto)

    # El acuse de recibo cierra la medición de latencia de un comando.
    if topic.endswith("/ack"):
        try:
            cmd_id = json.loads(texto).get("cmd_id")
        except json.JSONDecodeError:
            cmd_id = None
        resultado = estado.cerrar_comando(cmd_id) if cmd_id else None
        if resultado:
            bus.emitir("latencia", **resultado)

    # El topic de estado es donde aparece el testamento (LWT).
    if topic.endswith("/estado"):
        bus.emitir(
            "estado_dispositivo",
            topic=topic,
            valor=texto,
            retenido=bool(mensaje.retain),
        )

    # La telemetría es lo que cuenta para el comparador.
    if topic.endswith("/telemetria"):
        estado.anotar_mensaje("mqtt", desglose["bytes_total"], desglose["bytes_utiles"])

    bus.emitir(
        "paquete",
        protocolo="mqtt",
        topic=topic,
        qos=mensaje.qos,
        retenido=bool(mensaje.retain),
        **desglose,
    )


def iniciar() -> None:
    global _cliente
    _cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="lab-espia")
    _cliente.on_connect = _al_conectar
    _cliente.on_disconnect = _al_desconectar
    _cliente.on_message = _al_recibir
    _cliente.connect_async(HOST, PUERTO, keepalive=30)
    _cliente.loop_start()


def detener() -> None:
    if _cliente is not None:
        _cliente.loop_stop()
        _cliente.disconnect()


def publicar(topic: str, carga: str, qos: int = 1, retener: bool = False) -> None:
    if _cliente is None:
        raise RuntimeError("el espía MQTT no está iniciado")
    _cliente.publish(topic, carga, qos=qos, retain=retener)
