# Ejemplos: tu propio cliente MQTT

Dos clientes mínimos que se conectan al broker del laboratorio: uno en
**Python**, para tu computadora, y uno para un **ESP32**.

Todo lo que publiques con ellos aparece en la interfaz del laboratorio
(<http://localhost:8000>), en las pestañas **Inspector** y **Topics**, junto al
dispositivo simulado. Eso es lo que convierte el laboratorio en un banco de
pruebas y no en una demo.

---

## Antes de empezar: enciende el broker

Los ejemplos no traen broker: usan el que ya corre en Docker. Desde
`labs/02-protocolos`:

```bash
docker compose up -d
```

El broker queda escuchando en el puerto **1883** de tu computadora.

---

## Ejemplos de Python

| Archivo | Qué hace |
|---|---|
| `python/publicar.py` | **Transmite**: envía una muestra cada 5 segundos |
| `python/suscribir.py` | **Recibe**: muestra todo lo que pase por el broker |

Hay dos formas de ejecutarlos. **Si puedes, usa la opción A**: es la que vas a
usar el resto del curso, cuando escribas código contra AWS.

### Opción A — Python en tu computadora *(recomendada)*

**Requisitos:**

- **Python 3.13** o superior → <https://www.python.org/downloads/>
  En Windows, marca **"Add python.exe to PATH"** durante la instalación.
- La librería `paho-mqtt`.

Comprueba que Python está instalado:

```bash
python --version
```

Instala la librería, desde la carpeta `ejemplos/python`:

```bash
pip install -r requirements.txt
```

Y ahora, **en dos terminales distintas**:

```bash
python suscribir.py
```

```bash
python publicar.py
```

En la primera verás aparecer lo que envía la segunda. Para detener cualquiera
de las dos: `Ctrl + C`.

### Opción B — sin instalar nada, dentro de Docker

Si no puedes instalar Python, Docker ejecuta los mismos archivos. Desde
`labs/02-protocolos`:

```bash
docker compose run --rm cliente python publicar.py
```

```bash
docker compose run --rm cliente python suscribir.py
```

La primera vez tarda un poco porque construye la imagen. Funciona igual, con
una diferencia: dentro de Docker el broker no se llama `localhost` sino
`broker`, que es su nombre en la red interna de los contenedores. Por eso los
scripts leen la variable `MQTT_HOST` en vez de tener la dirección escrita a
mano.

> Ese detalle no es un truco del laboratorio: es exactamente el tipo de cosa
> que vas a configurar cuando el broker esté en AWS en vez de en tu PC.

### Personalizar sin tocar el código

```bash
DISPOSITIVO_ID=sensor-cesar python publicar.py
TOPIC=fablab/planta1/sensor-cesar/telemetria python suscribir.py
```

En PowerShell las variables se ponen antes, en otra línea:

```powershell
$env:DISPOSITIVO_ID = "sensor-cesar"; python publicar.py
```

**Cambia el identificador por uno tuyo.** Dos clientes conectados con el mismo
`client-id` se expulsan mutuamente del broker, y el síntoma —reconexiones
infinitas— es de los más difíciles de diagnosticar.

---

## Ejemplo para ESP32

Carpeta `esp32/mqtt_esp32/`. El sketch publica una muestra cada 5 segundos y
escucha su topic de comandos.

**Requisitos:**

- **IDE de Arduino** con el paquete de placas **esp32** de Espressif.
- La librería **PubSubClient**, de Nick O'Leary (Gestor de librerías).
- Un cable USB que transmita datos, no solo cargue.
- El ESP32 y tu computadora en la **misma red Wi-Fi**.

### 1. Averigua la IP de tu computadora

El ESP32 no puede usar `localhost`: para él, `localhost` es él mismo. Necesita
la dirección de tu PC en la red:

```powershell
ipconfig
```

```bash
ifconfig | grep "inet "
```

Busca algo como `192.168.1.45`. Si aparecen varias, usa la del adaptador por el
que estás conectado a la misma red que el ESP32.

### 2. Abre el puerto en el cortafuegos, si hace falta

Docker suele dejarlo abierto solo. Compruébalo desde **otra** máquina de la red
—un segundo portátil, o el teléfono con una app MQTT— apuntando a la IP del
paso anterior. Si no conecta, en **PowerShell como administrador**:

```powershell
New-NetFirewallRule -DisplayName "MQTT laboratorio" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow
```

Al terminar la clase conviene quitarla, porque este broker no pide contraseña:

```powershell
Remove-NetFirewallRule -DisplayName "MQTT laboratorio"
```

### 3. Edita las cuatro constantes del sketch

```cpp
const char* WIFI_SSID     = "NOMBRE_DE_TU_WIFI";
const char* WIFI_PASSWORD = "CLAVE_DE_TU_WIFI";
const char* MQTT_HOST     = "192.168.1.100";   // la IP del paso 1
const char* ID            = "esp32-01";        // único por alumno
```

### 4. Súbelo y abre el monitor serie a 115200 baudios

Deberías ver la conexión al Wi-Fi, la conexión al broker y una línea por cada
envío. Al mismo tiempo, tus mensajes aparecerán en la interfaz del laboratorio.

### 5. Mándale un comando

Desde tu computadora, con el laboratorio corriendo:

```bash
docker compose exec broker mosquitto_pub -t "fablab/planta1/esp32-01/comandos" -m "2"
```

El ESP32 lo recibe al instante —sin preguntar nada— y pasa a publicar cada 2
segundos. Eso es el *push* del que habla la teoría, ocurriendo en tu placa.

---

## Problemas frecuentes

| Síntoma | Qué pasa |
|---|---|
| `ModuleNotFoundError: No module named 'paho'` | Falta `pip install -r requirements.txt`, o lo instalaste en otro Python |
| `python` no se reconoce (Windows) | No está en el PATH: reinstala marcando "Add python.exe to PATH", o usa la opción B |
| `ConnectionRefusedError` | El laboratorio no está levantado: `docker compose up -d` |
| En el ESP32, `rc=-2` una y otra vez | IP equivocada, otra red Wi-Fi, o el cortafuegos bloqueando el 1883 |
| El ESP32 se reconecta sin parar | Dos equipos con el mismo `ID`: cámbialo |
| Publico pero no lo veo en la interfaz | Mira la pestaña **Topics**: si tu topic no empieza por `fablab/`, no coincide con el filtro |

---

## Lo que viene después

Estos clientes hablan con un broker sin autenticación en tu red local. En la
clase de **AWS IoT Core** el cambio es pequeño en el código y grande en el
concepto: la misma librería, el mismo `publish`, pero con el endpoint de AWS,
el puerto 8883 y un **certificado X.509 por dispositivo** en lugar de nada.
