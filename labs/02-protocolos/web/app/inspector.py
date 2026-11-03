"""Reconstrucción byte a byte de lo que viaja por la red.

HONESTIDAD INTELECTUAL: esto NO es una captura de red. Es una reconstrucción
fiel de la trama a partir de los datos reales del mensaje (los mismos bytes,
en el mismo orden y con el mismo formato que define cada protocolo). Se hace
así para no necesitar un contenedor con privilegios de red, que en Windows con
WSL2 da más problemas que valor pedagógico.

Si quieres la captura real, en clase: `tcpdump -i any -A port 1883`.
"""

from __future__ import annotations


# --- HTTP ----------------------------------------------------------------


def reconstruir_http(
    metodo: str,
    ruta: str,
    cabeceras_crudas: list[tuple[bytes, bytes]],
    cuerpo: bytes,
) -> dict:
    """Arma el texto exacto de una petición HTTP/1.1.

    Se usan las cabeceras crudas del scope ASGI para respetar el nombre tal
    como lo envió el cliente, no la versión normalizada del framework.
    """
    linea_peticion = f"{metodo} {ruta} HTTP/1.1\r\n"
    cabeceras = "".join(
        f"{nombre.decode('latin-1')}: {valor.decode('latin-1')}\r\n"
        for nombre, valor in cabeceras_crudas
    )
    texto = linea_peticion + cabeceras + "\r\n" + cuerpo.decode("utf-8", "replace")

    return {
        "texto": texto,
        "bytes_total": len(texto.encode("utf-8")),
        "bytes_utiles": len(cuerpo),
        "partes": [
            {"etiqueta": "Línea de petición", "bytes": len(linea_peticion), "clase": "overhead"},
            {"etiqueta": f"Cabeceras ({len(cabeceras_crudas)})", "bytes": len(cabeceras), "clase": "overhead"},
            {"etiqueta": "Línea en blanco", "bytes": 2, "clase": "overhead"},
            {"etiqueta": "Cuerpo (tu dato)", "bytes": len(cuerpo), "clase": "util"},
        ],
    }


def reconstruir_respuesta_http(codigo: int, bytes_cuerpo: int) -> str:
    nombres = {
        200: "OK",
        201: "Created",
        400: "Bad Request",
        401: "Unauthorized",
        429: "Too Many Requests",
        503: "Service Unavailable",
    }
    return f"HTTP/1.1 {codigo} {nombres.get(codigo, '')}".strip()


# --- MQTT ----------------------------------------------------------------


def _bytes_de_longitud(restante: int) -> int:
    """MQTT codifica la longitud restante en 1 a 4 bytes de ancho variable."""
    ancho = 1
    while restante >= 128:
        restante //= 128
        ancho += 1
    return ancho


def desglosar_mqtt(topic: str, carga: bytes, qos: int) -> dict:
    """Calcula el tamaño real de un paquete PUBLISH y lo desglosa.

    Estructura: cabecera fija (1 byte de tipo+flags + longitud variable),
    cabecera variable (2 bytes de longitud del topic + el topic + 2 bytes de
    identificador si QoS > 0) y el payload.
    """
    topic_bytes = topic.encode("utf-8")
    id_paquete = 2 if qos > 0 else 0
    restante = 2 + len(topic_bytes) + id_paquete + len(carga)
    ancho_longitud = _bytes_de_longitud(restante)
    total = 1 + ancho_longitud + restante

    partes = [
        {"etiqueta": "Tipo + flags", "bytes": 1, "clase": "overhead"},
        {"etiqueta": "Longitud restante", "bytes": ancho_longitud, "clase": "overhead"},
        {"etiqueta": "Longitud del topic", "bytes": 2, "clase": "overhead"},
        {"etiqueta": f"Topic ({topic})", "bytes": len(topic_bytes), "clase": "topic"},
    ]
    if id_paquete:
        partes.append({"etiqueta": "Id de paquete (QoS>0)", "bytes": 2, "clase": "overhead"})
    partes.append({"etiqueta": "Payload (tu dato)", "bytes": len(carga), "clase": "util"})

    texto = (
        f"PUBLISH  (QoS {qos})\n"
        f"  cabecera fija      : {1 + ancho_longitud} B\n"
        f"  topic              : {topic}  ({len(topic_bytes)} B)\n"
        f"  payload            : {carga.decode('utf-8', 'replace')}\n"
        f"  --------------------------------\n"
        f"  total en la red    : {total} B"
    )

    return {
        "texto": texto,
        "bytes_total": total,
        "bytes_utiles": len(carga),
        "partes": partes,
    }
