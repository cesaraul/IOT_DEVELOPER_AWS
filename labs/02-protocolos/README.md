# Laboratorio 02 — Protocolos IoT: HTTP y MQTT

Un sensor simulado envía **el mismo dato por HTTP y por MQTT al mismo tiempo**.
Tú ves, en vivo, los bytes que viajan por cada camino, y puedes romper el
sistema a propósito para observar cómo reacciona cada protocolo.

Todo corre en tu máquina. **No necesitas cuenta de AWS ni conexión a internet**
(salvo la primera vez, para construir las imágenes).

---

## Arrancar

> **¿Primera vez con Docker?** Empieza por la
> [guía de instalación paso a paso](../../docs/instalar-docker.md): instala
> Docker, comprueba que funciona y levanta este laboratorio, con las soluciones
> a los errores más comunes. Vuelve aquí cuando lo tengas corriendo.

Dentro de esta carpeta (`labs/02-protocolos`):

```bash
docker compose up --build
```

La primera vez tarda entre 2 y 5 minutos porque descarga las imágenes.

Cuando termine, abre **<http://localhost:8000>**.

> En la cabecera, el control **Tamaño** amplía o reduce toda la interfaz (70 % a
> 200 %) y recuerda tu elección en ese navegador. Útil para proyectar en el
> aula sin tocar el zoom del navegador.

Para detenerlo: `Ctrl+C`, y `docker compose down` para limpiar.

Qué se levanta:

| Servicio | Puerto | Qué es |
|---|---|---|
| `web` | 8000 | La interfaz y la API HTTP del laboratorio (FastAPI) |
| `broker` | 1883 / 9001 | Mosquitto: MQTT sobre TCP y sobre WebSockets |
| `simulador` | — | El dispositivo simulado, hablando por los dos protocolos |

---

## Cómo está organizado

El menú lateral tiene dos secciones, y conviene recorrerlas en orden.

### Fundamentos — un protocolo a la vez

**HTTP paso a paso.** Qué ocurre exactamente cuando un dispositivo envía una
medición: saludo TCP, negociación TLS, petición, respuesta y cierre, mensaje a
mensaje y con el contador de bytes sumando en vivo. Cinco escenarios: conexión
nueva, keep-alive, un `503` con backoff, un `400` que no hay que reintentar, y
el costo del polling. Incluye la tabla de códigos de estado leída como
decisiones de firmware.

**MQTT paso a paso.** Los mecanismos por separado, en nueve escenarios: CONNECT
y SUBSCRIBE, PUBLISH con QoS 0, QoS 1 con su PUBACK perdido y el duplicado,
QoS 2, el enrutado del broker hacia varios suscriptores, el keepalive, los
mensajes retenidos, la sesión persistente y el testamento.

Los dos usan el mismo reproductor: reproducir, pausar, ir paso a paso, volver
atrás y cambiar la velocidad. Cada mensaje trae su explicación y su tamaño.

### Laboratorio en vivo — tráfico real

**Comparador.** Los dos canales, lado a lado, con la proyección de MB al
mes. Fíjate en la *eficiencia*: el porcentaje de lo que viaja que de verdad es
tu medición.

**Inspector de paquetes.** Cada mensaje, byte a byte, con el desglose
coloreado: rojo lo que es protocolo, naranja el nombre del topic, verde tu dato.
Haz clic en cualquier línea para desplegarla.

**Comandos y latencia.** Manda la misma orden por HTTP y por MQTT y
cronométralas. Por HTTP el dispositivo se entera cuando le toca preguntar; por
MQTT el broker se la empuja.

**Topics.** Tu navegador está suscrito al broker: es un suscriptor más.
Escribe patrones con `+` y `#` y mira qué topics coinciden.

**Laboratorio de fallos.** Inyecta errores `503` y `429`, añade latencia o
corta la red del dispositivo. Observa el backoff exponencial, la cola local y
el testamento (LWT) de MQTT.

**QoS y retención.** Desconecta el suscriptor, publica con QoS 0 y 1, y
vuelve a conectarlo con y sin sesión limpia. Comprueba qué sobrevive.

---

## Ejercicios

### HTTP

**L1 — Ver el protocolo.** Con el laboratorio corriendo:

```bash
curl -v -X POST http://localhost:8000/telemetry \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-key" \
  -d '{"temp":23.4,"nivel":87}'
```

Tu petición aparecerá en el inspector. Identifica la línea de petición, las
cabeceras y el cuerpo. *(También puedes probar la API desde
<http://localhost:8000/docs>.)*

**L2 — Medir el overhead.** Calcula qué porcentaje de la petición es tu dato, y
multiplica los bytes por mensaje por 259.200 envíos al mes.

**L3 — Un cliente que aguanta.** Escribe un cliente que envíe telemetría y
sobreviva a los fallos. Activa en la pestaña 5 un 40% de respuestas `503` y
comprueba que el tuyo:

- no reintenta ante un `400` (ese error es tuyo, no del servidor),
- reintenta con backoff exponencial **y jitter** ante `503` y `429`,
- guarda en una cola local lo que no pudo enviar.

**L4 — El dolor del polling.** Haz `GET /config` en bucle y mide cuánto tardas
en enterarte de un cambio de configuración.

### MQTT

**L1 — Pub/sub a mano**, en dos terminales:

```bash
mosquitto_sub -h localhost -t "fablab/#" -v
```

```bash
mosquitto_pub -h localhost -t "fablab/planta1/mi-sensor/telemetria" -m '{"temp":23.4}'
```

**L2 — El mismo sensor, en MQTT.** Publica telemetría con `paho-mqtt` y compara
los bytes con los de L2 de HTTP.

**L3 — La nube habla primero.** Suscríbete a
`fablab/planta1/mi-sensor/comandos` y mide la latencia de un comando.

**L4 — LWT y retención.** Configura un testamento, publica tu estado con
`retain=True`, y mata tu proceso de golpe. Mira la pestaña 5.

**L5 — QoS y sesión persistente.** Usa la pestaña 6.

---

## Conectar tus propios scripts

El laboratorio no es solo una demo: **tus clientes pueden entrar al mismo
sistema** y aparecerán en la interfaz junto al dispositivo simulado.

```python
# HTTP
import requests
requests.post("http://localhost:8000/telemetry",
              json={"temp": 25.0, "nivel": 50},
              headers={"Authorization": "Bearer demo-key"})

# MQTT
import paho.mqtt.client as mqtt
cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mi-sensor")
cliente.connect("localhost", 1883)
cliente.publish("fablab/planta1/mi-sensor/telemetria", '{"temp":25.0}')
```

Usa **un client-id distinto** del de tus compañeros y del simulador
(`tanque-03`): dos clientes con el mismo id se expulsan mutuamente del broker.

---

## Si Docker no arranca

Puedes correr las tres piezas a mano:

```bash
# 1. Broker
mosquitto -c broker/mosquitto.conf
```

```bash
# 2. Servidor web
cd web && pip install -r requirements.txt && uvicorn app.main:aplicacion --port 8000
```

```bash
# 3. Dispositivo simulado
cd simulador && pip install -r requirements.txt && python dispositivo.py
```

---

## Estructura

```
labs/02-protocolos/
├── docker-compose.yml
├── broker/mosquitto.conf       Configuración del broker
├── web/
│   ├── app/main.py             API del dispositivo + API del laboratorio
│   ├── app/inspector.py        Reconstrucción byte a byte de las tramas
│   ├── app/espia.py            Suscriptor a '#' que alimenta la interfaz
│   ├── app/estado.py           Métricas y configuración en memoria
│   ├── app/eventos.py          Bus de eventos hacia el navegador
│   └── static/
│       ├── js/guiones.js       Los escenarios paso a paso (son datos)
│       ├── js/componentes/     Vistas Vue, una por pantalla
│       └── vendor/             Vue, GSAP y MQTT.js, sin CDN ni npm
└── simulador/dispositivo.py    El sensor simulado: léelo, es el ejemplo
```

**Sobre el frontend:** Vue 3 y GSAP cargan como archivos sueltos, igual que
MQTT.js. No hay `npm`, ni `node_modules`, ni paso de compilación: lo que lees
es lo que corre. Para añadir un escenario nuevo a las animaciones basta con
agregarlo a `static/js/guiones.js`, que es una lista de mensajes con su tamaño
y su explicación.

**El código es parte del material.** `dispositivo.py` es el mismo cliente que
escribes en los laboratorios, con los dos protocolos juntos para poder
compararlos.

---

## Dos advertencias

**El inspector reconstruye las tramas, no captura la red.** Son los mismos
bytes, en el mismo orden y con el mismo formato que define cada protocolo,
calculados a partir del mensaje real. Se hace así para no necesitar un
contenedor con privilegios de red. Si quieres la captura de verdad:
`tcpdump -i any -A port 1883`.

**Este laboratorio es inseguro a propósito.** El broker acepta conexiones
anónimas, el puerto 1883 va sin cifrar y la clave de la API es `demo-key`
escrita en el código. Está bien para aprender en tu máquina y **estaría muy mal
en producción**. En la clase de AWS IoT Core verás cómo se hace de verdad: un
certificado X.509 por dispositivo y políticas de permisos por topic.
