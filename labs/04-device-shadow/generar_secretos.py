"""Genera el secretos.h del ESP32 de ESTE laboratorio, con tus certificados.

POR QUÉ EXISTE ESTE ARCHIVO
    El ESP32 no tiene dónde guardar archivos sueltos: los certificados hay
    que compilarlos DENTRO del programa, como texto. Eso crea un problema
    que no teníamos en Python, donde la llave vivía en su propio archivo y
    bastaba con no subir esa carpeta.

    Si pegaras tu llave privada en el .ino, cualquiera que viera ese archivo
    podría hacerse pasar por tu dispositivo. Y los .ino se comparten todo el
    tiempo: por correo, en un USB, en un repositorio.

    Así que el código va en un archivo y los secretos en otro. Este script
    lee tu carpeta 'certificados' (la del laboratorio 03, que es la que usa
    todo el laboratorio 04) y escribe el secretos.h con el formato que
    entiende el compilador de Arduino.

CÓMO SE EJECUTA
    docker compose run --rm dispositivo python generar_secretos.py

    Luego abre el sketch en el IDE de Arduino: secretos.h aparece como una
    pestaña más, al lado del .ino. Ahí escribes tu WiFi.

LO QUE TIENES QUE SABER
    Si cambias de dispositivo, cambia DISPOSITIVO_ID en el .env del
    laboratorio 03 y vuelve a ejecutar esto. Nunca edites secretos.h a mano
    para cambiar certificados: es más fácil equivocarse copiando que volver
    a generarlo.
"""

import os

import config

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, "esp32", "aws_shadow_esp32", "secretos.h")


def leer(ruta: str) -> str:
    """Devuelve el contenido de un .pem sin líneas en blanco al final."""
    with open(ruta, "r", encoding="utf-8") as archivo:
        return archivo.read().strip()


def bloque(nombre: str, contenido: str) -> str:
    """Envuelve un certificado en la sintaxis que entiende Arduino.

    R"EOF( ... )EOF" es un 'raw string literal' de C++: todo lo que hay
    dentro se toma literal, con sus saltos de línea incluidos. Sin eso
    habría que escribir cada línea entre comillas y terminarla con \\n, que
    es exactamente el tipo de tarea en la que uno se equivoca.

    PROGMEM le dice al compilador que guarde el texto en la memoria de
    programa (flash) y no en la RAM. Importa: los tres certificados juntos
    pasan de 4 KB, y el ESP32 necesita su RAM para la conexión TLS y para
    el buffer de MQTT, que en este laboratorio es grande.
    """
    return f'static const char {nombre}[] PROGMEM = R"EOF(\n{contenido}\n)EOF";\n'


def main() -> None:
    rutas = config.identidad()
    if not rutas:
        config.abandonar("Faltan los certificados. ¿Hiciste el laboratorio 03?")

    cert, llave, raiz = rutas

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)

    partes = [
        "// ARCHIVO GENERADO. No lo subas a ningún repositorio.",
        "//",
        "// Lo creó generar_secretos.py a partir de tu carpeta 'certificados'.",
        "// Para regenerarlo:",
        "//     docker compose run --rm dispositivo python generar_secretos.py",
        "//",
        "// Lo único que tienes que escribir a mano es tu WiFi, aquí abajo.",
        "",
        "#ifndef SECRETOS_H",
        "#define SECRETOS_H",
        "",
        "// --- Tu red WiFi -------------------------------------------------------",
        "// El ESP32 solo habla WiFi de 2,4 GHz. Si tu router emite 2,4 y 5 GHz con",
        "// el mismo nombre, puede que tengas que separarlos para que encuentre la red.",
        '#define SECRETO_WIFI_SSID      "NOMBRE_DE_TU_WIFI"',
        '#define SECRETO_WIFI_PASSWORD  "CLAVE_DE_TU_WIFI"',
        "",
        "// --- Tu cuenta de AWS --------------------------------------------------",
        f'#define SECRETO_AWS_ENDPOINT   "{config.ENDPOINT}"',
        f'#define SECRETO_DISPOSITIVO_ID "{config.ID}"',
        "",
        "// --- Tus certificados --------------------------------------------------",
        f"// raíz de Amazon:  {os.path.basename(raiz)}",
        "",
        bloque("SECRETO_ROOT_CA", leer(raiz)),
        f"// tu certificado:  {os.path.basename(cert)}",
        "",
        bloque("SECRETO_CERTIFICADO", leer(cert)),
        f"// tu llave privada: {os.path.basename(llave)}  <-- esto es lo que no se comparte",
        "",
        bloque("SECRETO_LLAVE_PRIVADA", leer(llave)),
        "#endif  // SECRETOS_H",
        "",
    ]

    with open(DESTINO, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(partes))

    print("\n  Escrito: esp32/aws_shadow_esp32/secretos.h")
    print(f"  Dispositivo: {config.ID}")
    print(f"  Endpoint:    {config.ENDPOINT}\n")
    print("  Ahora abre el sketch en el IDE de Arduino y escribe tu WiFi")
    print("  en la pestaña secretos.h. Nada más.\n")
    print("  Ese archivo NO se sube al repositorio: lleva tu llave privada.\n")
    print("  OJO: si vas a encender la placa, apaga antes el shadow_dispositivo.py")
    print("  de tu laptop. Los dos usan el mismo nombre de cliente y AWS")
    print("  expulsa a uno de los dos.\n")


if __name__ == "__main__":
    main()
