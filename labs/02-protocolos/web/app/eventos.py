"""Bus de eventos hacia el navegador.

El espía MQTT corre en su propio hilo (paho) y el servidor HTTP en el bucle
asíncrono. Para no pelear con dos mundos distintos, los eventos entran en una
cola que sí es segura entre hilos, y una tarea asíncrona la vacía y los reparte
por WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import queue
import time
from collections import deque

from fastapi import WebSocket


class Bus:
    def __init__(self, historial: int = 80) -> None:
        self._cola: queue.SimpleQueue = queue.SimpleQueue()
        self._clientes: set[WebSocket] = set()
        self._historial: deque = deque(maxlen=historial)

    # -- entrada (desde cualquier hilo) -----------------------------------

    def emitir(self, tipo: str, **datos) -> None:
        self._cola.put({"tipo": tipo, "ts": time.time(), **datos})

    # -- salida (bucle asíncrono) -----------------------------------------

    async def conectar(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clientes.add(ws)
        # Quien llega tarde ve lo último que pasó, no una pantalla vacía.
        for evento in list(self._historial):
            await ws.send_text(json.dumps(evento))

    def desconectar(self, ws: WebSocket) -> None:
        self._clientes.discard(ws)

    async def repartir_siempre(self) -> None:
        while True:
            repartidos = 0
            while repartidos < 200:
                try:
                    evento = self._cola.get_nowait()
                except queue.Empty:
                    break
                repartidos += 1
                if evento["tipo"] in ("paquete", "aviso"):
                    self._historial.append(evento)
                await self._repartir(evento)
            await asyncio.sleep(0.05)

    async def _repartir(self, evento: dict) -> None:
        if not self._clientes:
            return
        mensaje = json.dumps(evento)
        caidos = []
        for ws in list(self._clientes):
            try:
                await ws.send_text(mensaje)
            except Exception:
                caidos.append(ws)
        for ws in caidos:
            self._clientes.discard(ws)


bus = Bus()
