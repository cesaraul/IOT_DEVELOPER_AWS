# Preparar tu computadora para los laboratorios

Guía paso a paso para instalar Docker y levantar los laboratorios del curso.
**No hace falta saber Docker.** Son cuatro comandos en total y aquí está cada
uno explicado.

Dedícale 20 minutos **antes** de la clase. Si algo falla, al final hay una
sección de problemas frecuentes con la solución de cada uno.

---

## Índice

1. [¿Qué vamos a instalar y por qué?](#1-qué-vamos-a-instalar-y-por-qué)
2. [Instalar Docker en Windows](#2-instalar-docker-en-windows)
3. [Instalar Docker en macOS](#3-instalar-docker-en-macos)
4. [Instalar Docker en Linux](#4-instalar-docker-en-linux)
5. [Comprobar que funciona](#5-comprobar-que-funciona)
6. [Descargar el material del curso](#6-descargar-el-material-del-curso)
7. [Levantar tu primer laboratorio](#7-levantar-tu-primer-laboratorio)
8. [Apagarlo](#8-apagarlo)
9. [Problemas frecuentes](#9-problemas-frecuentes)
10. [Chuleta de comandos](#10-chuleta-de-comandos)

---

## 1. ¿Qué vamos a instalar y por qué?

Los laboratorios del curso necesitan varias piezas funcionando a la vez: un
servidor web, un broker MQTT, un dispositivo simulado. Instalarlas una por una
en tu computadora sería lento, distinto en cada sistema operativo, y dejaría
tu máquina llena de cosas que no vas a volver a usar.

**Docker** resuelve eso: descarga cada pieza ya preparada, la ejecuta aislada
del resto de tu sistema, y cuando terminas la borra sin dejar rastro. Un solo
comando levanta todo el laboratorio, y es idéntico en Windows, macOS y Linux.

Es además una herramienta que vas a encontrar en cualquier equipo de desarrollo
profesional, así que el rato que inviertas aquí te sirve más allá del curso.

> **Nota:** Docker necesita internet la **primera** vez, para descargar las
> piezas. Después los laboratorios funcionan sin conexión.

---

## 2. Instalar Docker en Windows

### Antes de empezar, comprueba que tu equipo cumple

- Windows 10 (versión 22H2 o posterior) o Windows 11, de 64 bits.
- Al menos **8 GB de RAM** (con 4 GB funciona, pero irá justo).
- Unos **5 GB libres** en disco.
- La **virtualización activada** en la BIOS. Para comprobarlo: abre el
  Administrador de tareas (`Ctrl + Shift + Esc`) → pestaña **Rendimiento** →
  **CPU**. Abajo a la derecha debe decir `Virtualización: Habilitada`.
  Si dice *Deshabilitada*, ve a la sección de problemas, punto
  [A](#a-virtualización-deshabilitada).

### Paso 1 — Instalar WSL 2

Docker en Windows se apoya en WSL (el subsistema de Linux para Windows). Abre
**PowerShell como administrador** (botón derecho sobre el menú Inicio →
*Terminal (Administrador)*) y ejecuta:

```powershell
wsl --install
```

Si te dice que ya está instalado, actualízalo:

```powershell
wsl --update
```

**Reinicia la computadora** cuando termine. Este paso es el que más problemas
da después si se lo salta, así que no lo dejes para luego.

### Paso 2 — Descargar e instalar Docker Desktop

1. Entra a <https://www.docker.com/products/docker-desktop/> y descarga
   **Docker Desktop for Windows**.
2. Ejecuta el instalador. Deja marcada la opción **Use WSL 2 instead of
   Hyper-V**.
3. Al terminar, **reinicia** si te lo pide.

### Paso 3 — Abrir Docker Desktop y dejarlo arrancar

Busca *Docker Desktop* en el menú Inicio y ábrelo. La primera vez:

- Acepta los términos de servicio.
- Si te ofrece crear una cuenta, puedes **saltarlo**: no hace falta para el
  curso.
- Espera a que abajo a la izquierda aparezca **"Engine running"** con un punto
  verde. Puede tardar un par de minutos la primera vez.

> **Importante:** Docker Desktop tiene que estar **abierto** para que los
> comandos funcionen. Si lo cierras, los laboratorios se detienen. Puedes
> configurarlo para que arranque solo con Windows en *Settings → General →
> Start Docker Desktop when you sign in*.

Ahora pasa a [comprobar que funciona](#5-comprobar-que-funciona).

---

## 3. Instalar Docker en macOS

1. Entra a <https://www.docker.com/products/docker-desktop/> y descarga
   **Docker Desktop for Mac**. Elige bien la versión:
   - **Apple Silicon** si tu Mac es M1, M2, M3 o posterior.
   - **Intel chip** si es un Mac anterior a 2020.
   - ¿No estás seguro? Menú Apple → *Acerca de este Mac*: si en *Chip* dice
     "Apple", es Apple Silicon.
2. Abre el `.dmg` descargado y arrastra **Docker** a la carpeta
   **Aplicaciones**.
3. Abre Docker desde Aplicaciones. macOS te pedirá la contraseña de tu usuario
   para instalar un componente del sistema: es normal.
4. Espera a que el icono de la ballena en la barra superior deje de animarse.

Ahora pasa a [comprobar que funciona](#5-comprobar-que-funciona).

---

## 4. Instalar Docker en Linux

En Ubuntu o Debian, el camino corto:

```bash
curl -fsSL https://get.docker.com | sudo sh
```

Después, añade tu usuario al grupo `docker` para no tener que escribir `sudo`
en cada comando:

```bash
sudo usermod -aG docker $USER
```

**Cierra la sesión y vuelve a entrar** para que el cambio tenga efecto.

En Linux no hay Docker Desktop: el servicio arranca solo con el sistema.

---

## 5. Comprobar que funciona

Abre una terminal —en Windows, **PowerShell**; en macOS, **Terminal**— y
ejecuta:

```bash
docker --version
```

Debe responder algo parecido a esto (el número puede ser distinto, da igual):

```
Docker version 29.9.2, build a82e528
```

Ahora comprueba Compose, que es la parte que levanta varias piezas a la vez:

```bash
docker compose version
```

```
Docker Compose version v5.6.1
```

Y por último, la prueba de fuego:

```bash
docker run hello-world
```

Si ves un mensaje que empieza con **"Hello from Docker!"**, está todo listo.
Ese mensaje significa que Docker descargó una pieza de internet, la ejecutó y
te devolvió su salida: exactamente lo que harán los laboratorios.

¿Algún comando falló? Ve a [problemas frecuentes](#9-problemas-frecuentes).

---

## 6. Descargar el material del curso

### Opción A — Con Git (recomendada)

Si tienes Git instalado, en la carpeta donde quieras guardar el curso:

```bash
git clone https://github.com/cesaraul/IOT_DEVELOPER_AWS.git
```

La ventaja: cuando publiquemos material nuevo, lo actualizas con un solo
comando dentro de esa carpeta:

```bash
git pull
```

### Opción B — Sin Git, descargando un ZIP

1. Entra a <https://github.com/cesaraul/IOT_DEVELOPER_AWS>.
2. Botón verde **Code** → **Download ZIP**.
3. Descomprime el archivo donde quieras.

Con esta opción tendrás que volver a descargar el ZIP cada vez que haya
material nuevo.

> **Consejo:** guarda el curso en una ruta **sin espacios ni acentos**, por
> ejemplo `C:\cursos\IOT_DEVELOPER_AWS`. Te ahorrará dolores de cabeza con
> rutas raras más adelante.

---

## 7. Levantar tu primer laboratorio

En la terminal, entra a la carpeta del laboratorio:

```bash
cd IOT_DEVELOPER_AWS/labs/02-protocolos
```

> En Windows, si guardaste el curso en `C:\cursos`, el comando completo sería
> `cd C:\cursos\IOT_DEVELOPER_AWS\labs\02-protocolos`.
>
> Truco: escribe `cd ` (con el espacio) y **arrastra la carpeta** desde el
> explorador a la terminal. La ruta se escribe sola.

Y ahora, el comando que lo levanta todo:

```bash
docker compose up --build
```

### Qué vas a ver

La primera vez tardará **entre 2 y 5 minutos**: está descargando Python,
Mosquitto y las librerías. Verás muchísimas líneas pasando; es normal y no
tienes que leerlas.

Sabrás que terminó cuando las líneas dejen de avanzar y veas algo así:

```
lab-broker     | mosquitto version 2.0.x running
lab-web        | INFO:     Uvicorn running on http://0.0.0.0:8000
lab-simulador  | [ok] Dispositivo 'tanque-03' en marcha
```

**Deja esa terminal abierta.** Mientras esté abierta, el laboratorio está
encendido.

### Abre el laboratorio

En tu navegador, entra a:

**<http://localhost:8000>**

### Cómo saber que todo está bien

- Arriba a la derecha hay una etiqueta verde que dice **"en vivo"**.
- En *Comparador*, los contadores de mensajes suben solos cada pocos segundos.
- En *Inspector*, van apareciendo paquetes nuevos.

Si ves eso, terminaste. Ya puedes explorar el menú de la izquierda.

---

## 8. Apagarlo

En la terminal donde está corriendo, pulsa **`Ctrl + C`**. Eso detiene el
laboratorio.

Para dejarlo todo limpio (borra los contenedores, no el material):

```bash
docker compose down
```

Puedes volver a levantarlo cuando quieras con `docker compose up`. La segunda
vez tarda segundos, porque ya no tiene que descargar nada.

---

## 9. Problemas frecuentes

### A. Virtualización deshabilitada

*Síntoma:* el instalador o Docker Desktop dice algo como
`Virtualization support not detected` o `WSL 2 requires virtualization`.

*Solución:* hay que activarla en la BIOS/UEFI. Reinicia y entra a la BIOS
pulsando `F2`, `F10`, `Supr` o `Esc` durante el arranque (depende del
fabricante). Busca una opción llamada **Intel VT-x**, **AMD-V**, **SVM Mode**
o **Virtualization Technology** y actívala. Guarda y reinicia.

Si no te animas a tocar la BIOS, avísame antes de la clase y vemos otra
alternativa: el laboratorio también se puede correr sin Docker (ver la sección
*Si Docker no arranca* del README del laboratorio).

### B. `docker: command not found` / `no se reconoce como un comando`

Docker Desktop no está instalado, o la terminal se abrió **antes** de
instalarlo. Cierra la terminal, ábrela de nuevo y reintenta. Si sigue igual,
reinicia la computadora.

### C. `Cannot connect to the Docker daemon`

Docker Desktop no está abierto o todavía está arrancando. Ábrelo y espera a que
diga **"Engine running"** en verde.

### D. `port is already allocated` o `bind: address already in use`

Algo en tu computadora ya está usando el puerto 8000, 1883 o 9001.

Para saber qué es, en Windows:

```powershell
netstat -ano | findstr :8000
```

El último número de la línea es el identificador del programa; búscalo en el
Administrador de tareas, pestaña *Detalles*, y ciérralo.

¿No puedes cerrarlo? Abre `docker-compose.yml` y cambia el primer número de la
línea del puerto. Por ejemplo, de `"8000:8000"` a `"8080:8000"`, y entra al
laboratorio por <http://localhost:8080>.

### E. `WSL 2 installation is incomplete` (Windows)

Abre PowerShell como administrador y ejecuta:

```powershell
wsl --update
```

Reinicia y vuelve a abrir Docker Desktop.

### F. La descarga de imágenes falla o se queda colgada

Casi siempre es la red: una VPN, un antivirus o el firewall de la institución
bloqueando la conexión. Prueba a **desactivar la VPN** y repetir. Si estás en
una red corporativa o universitaria con proxy, hazlo desde casa o desde una
conexión compartida del teléfono.

### G. La página carga pero dice "sin conexión" en vez de "en vivo"

El servidor web se reinició o aún está arrancando. Espera 10 segundos y
recarga. Si sigue, mira qué dice el servidor:

```bash
docker compose logs web
```

### H. No se ven mensajes en Topics o en QoS

Esas dos pantallas conectan tu navegador directamente al broker por el puerto
**9001**. Si tu firewall lo bloquea, el resto del laboratorio funciona pero esas
dos pantallas quedan vacías. Permite el puerto o repórtalo en clase.

### I. "Me quedé sin espacio en disco"

Docker guarda las piezas descargadas. Para liberar lo que ya no uses:

```bash
docker system prune -a
```

Ojo: eso borra todas las imágenes descargadas y la próxima vez volverá a
descargarlas.

### ¿Nada de esto funcionó?

Escríbeme **antes de la clase** con una captura del error completo. No llegues
el día de la sesión con el entorno sin probar: perderás la parte práctica, que
es la más importante.

---

## 10. Chuleta de comandos

Todos se ejecutan **dentro de la carpeta del laboratorio**.

| Comando | Qué hace |
|---|---|
| `docker compose up --build` | Levanta el laboratorio (la primera vez) |
| `docker compose up` | Lo levanta de nuevo, sin reconstruir |
| `docker compose up -d` | Lo levanta en segundo plano, sin ocupar la terminal |
| `docker compose ps` | Muestra qué está corriendo |
| `docker compose logs -f web` | Muestra en vivo lo que dice el servidor web |
| `docker compose restart` | Reinicia todo |
| `docker compose down` | Lo apaga y limpia |
| `Ctrl + C` | Detiene lo que está corriendo en esa terminal |

Con `docker compose ps` deberías ver las tres piezas del laboratorio:

```
NAME            STATUS                   PORTS
lab-broker      Up 2 minutes (healthy)   0.0.0.0:1883->1883/tcp, 0.0.0.0:9001->9001/tcp
lab-simulador   Up 2 minutes
lab-web         Up 2 minutes             0.0.0.0:8000->8000/tcp
```
