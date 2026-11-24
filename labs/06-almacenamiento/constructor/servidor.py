"""El servidor del constructor. Cuarenta líneas y ninguna dependencia.

POR QUÉ HACE FALTA UN SERVIDOR
    Una página web no puede escribir en una ruta de tu disco: el navegador
    no se lo permite, y menos mal. Lo único que podría hacer es ofrecerte
    una descarga, que acabaría en la carpeta Descargas con un nombre que
    no controlas.

    Como queremos que la plantilla se guarde EN SU SITIO —y que el comando
    que te enseñamos funcione tal cual, sin que copies nada—, hace falta
    algo que reciba el archivo y lo escriba. Eso es este programa.

    Hace dos cosas y nada más:
      GET  cualquier cosa  ->  sirve la página
      POST /guardar        ->  escribe la plantilla en la carpeta montada

QUÉ NO HACE, Y A PROPÓSITO
    No toca AWS. No sabe nada de tus credenciales, no las pide y no las
    necesita. Construye un archivo de texto; desplegarlo es cosa tuya,
    desde tu terminal, con tu perfil.

    Esa separación no es pereza: una herramienta de clase que tuviera tus
    claves sería una mala idea, y además no enseñaría el paso que importa.
"""

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Dentro del contenedor, la carpeta del laboratorio está montada aquí.
SALIDA = os.getenv("CARPETA_SALIDA", "/salida")
ARCHIVO = os.getenv("NOMBRE_ARCHIVO", "mi-clase6.yaml")

# La ruta tal como la ve el alumno en SU máquina. El contenedor no puede
# adivinarla, así que se la pasamos por el docker-compose. Sin esto, el
# comando que enseñamos en pantalla no serviría para copiar y pegar.
RUTA_HOST = os.getenv("RUTA_HOST", "labs/06-almacenamiento/mi-clase6.yaml")

PUERTO = int(os.getenv("PUERTO", "80"))


class Manejador(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Los archivos de la interfaz viven en web/.
        super().__init__(*args, directory="/srv/web", **kwargs)

    def do_POST(self):
        if self.path != "/guardar":
            self.send_error(404)
            return

        largo = int(self.headers.get("Content-Length", 0))
        yaml = self.rfile.read(largo).decode("utf-8")

        destino = os.path.join(SALIDA, ARCHIVO)
        with open(destino, "w", encoding="utf-8", newline="\n") as f:
            f.write(yaml)

        print(f"guardado: {destino}  ({len(yaml)} bytes)", flush=True)

        respuesta = json.dumps({"ok": True, "ruta": RUTA_HOST}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(respuesta)))
        self.end_headers()
        self.wfile.write(respuesta)

    def end_headers(self):
        # Sin caché. Esta herramienta se va a corregir entre clases, y un
        # navegador que se queda con el JavaScript viejo carga la página
        # perfectamente y no funciona, sin un solo error visible.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, formato, *args):
        # Silenciamos el registro de cada archivo servido: en clase solo
        # estorba. Los guardados sí se imprimen, arriba.
        pass


if __name__ == "__main__":
    print(f"Constructor en marcha. Guardará en {RUTA_HOST}", flush=True)
    ThreadingHTTPServer(("", PUERTO), Manejador).serve_forever()
