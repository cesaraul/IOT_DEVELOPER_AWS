# Laboratorio 04 — Device Shadow: el gemelo digital

En el laboratorio anterior mandaste un comando y el dispositivo lo recibió.
Pero solo si estaba encendido. **Si estaba apagado, el comando se perdió para
siempre** — y nadie te avisó, porque nadie hizo nada mal.

Al terminar este laboratorio vas a poder **apagar tu dispositivo, darle una
orden, encenderlo, y verlo obedecer**.

---

## Antes de empezar

Necesitas el **laboratorio 03 funcionando**. Este reutiliza sus certificados
y su `.env`: no hay que descargar nada nuevo de AWS.

```bash
cd ../03-iot-core
docker compose run --rm aws python comprobar.py
```

Si no sale todo en verde, arregla eso primero. Aquí no va a funcionar nada.

---

## La idea, en tres frases

Un **shadow** es un documento JSON que vive en AWS, uno por dispositivo, y
guarda dos cosas:

- **`reported`** — lo que el dispositivo **dice que es**. Lo escribe él.
- **`desired`** — lo que nosotros **queremos que sea**. Lo escribe la aplicación.

Cuando las dos no coinciden, AWS calcula la diferencia —el **`delta`**— y se
la entrega al dispositivo. Si el dispositivo está apagado, la diferencia
**espera**. Esa espera es todo lo que este laboratorio añade.

```
app  ──escribe desired──►  SHADOW  ──entrega delta──►  dispositivo
                              ▲                              │
                              └────escribe reported──────────┘
```

> **Las tres reglas.** El dispositivo escribe `reported` y nunca `desired`.
> La aplicación escribe `desired` y nunca `reported`. El `delta` no lo
> escribe nadie: lo calcula AWS.

---

## Dos actores, dos identidades

Esto es lo segundo que trae el laboratorio, y es tan importante como el
shadow. Hasta ahora todo entraba a AWS con el certificado del dispositivo.
Hoy entra también una **aplicación**, y una aplicación **no es** un
dispositivo:

| | Dispositivo | Aplicación |
|---|---|---|
| Quién es | el equipo en la planta | un backend, una web, una app |
| Se identifica con | **certificado X.509** | **claves de un usuario de IAM** |
| Habla por | MQTT, puerto 8883 | API HTTPS de AWS |
| Librería | `paho-mqtt` | `boto3` (el SDK de AWS) |
| Escribe | `reported` | `desired` |
| Archivo | `shadow_dispositivo.py` | `shadow_app.py` |

¿Por qué no usar el certificado del dispositivo también en la aplicación, y
ahorrarse el usuario de IAM? Porque si tu backend lleva dentro el certificado
del sensor, **cualquiera que entre al backend puede hacerse pasar por ese
sensor**. Y el día que retires el sensor y revoques su certificado, tu backend
deja de funcionar. Dos actores, dos identidades.

Mira el `docker-compose.yml`: el servicio `app` **no monta la carpeta de
certificados**. No los tiene porque no debe tenerlos.

---

## Paso 1 · Los permisos (los dos)

La política del laboratorio 03 autoriza `fablab/planta1/*` y nada más. Los
topics del shadow empiezan por `$aws/things/...`, que no cae ahí dentro.
**Este laboratorio no va a funcionar hasta que amplíes la política** — y esa
es la lección, no un accidente: lo que no está escrito, no se puede.

Genera tus dos políticas:

```bash
docker compose run --rm dispositivo python generar_politica.py
```

El script lee el archivo `-Policy` que vino dentro de tu *connection kit*,
saca de ahí tu **número de cuenta** y tu **región**, y escribe dos archivos:

| Archivo | Para quién | Dónde se pega |
|---|---|---|
| `mi-politica.json` | el **certificado** del dispositivo | IoT Core → *Security* → *Policies* → tu política → *Edit* |
| `mi-politica-app.json` | el **usuario de IAM** de la aplicación | IAM → *Usuarios* → tu usuario → *Permisos* → política en línea |

> ### El error número uno de este paso
>
> Al guardar la política del dispositivo, marca **«Establecer como versión
> activa»**. Si no lo haces, se crea una versión nueva que **no se aplica a
> nada**: guarda bien, no da error, y no cambia nada. Luego pasas media hora
> buscando el fallo en otro sitio.

---

## Paso 2 · Las claves de la aplicación

El usuario de IAM que creaste en la clase 3 todavía no ha hecho nada. Hoy
trabaja.

1. **IAM** → **Usuarios** → tu usuario → pestaña **Credenciales de seguridad**.
2. **Crear clave de acceso** → caso de uso *«Aplicación que se ejecuta fuera
   de AWS»*.
3. Copia las dos cadenas.

> **La clave secreta se muestra una sola vez.** Es la misma regla que la
> llave privada del certificado. Si cierras esa ventana sin copiarla, se
> borra esa clave y se crea otra: treinta segundos, pero mejor no pasar por
> ahí.

Pégalas en el `.env` de **esta** carpeta:

```bash
cp .env.example .env
```

```powershell
Copy-Item .env.example .env
```

```ini
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

Ese archivo está en el `.gitignore`. Esas claves valen tanto como una
contraseña: con ellas se entra a tu cuenta de AWS.

---

## Paso 3 · Comprobar

```bash
docker compose run --rm dispositivo python comprobar.py
```

Revisa las dos mitades por separado —el dispositivo con su certificado, la
aplicación con sus claves— y te dice exactamente qué falta en cada una.

**No sigas hasta que todo salga en verde.**

---

## Paso 4 · El dispositivo que obedece

Arranca el equipo:

```bash
docker compose run --rm dispositivo python shadow_dispositivo.py
```

Mira lo que imprime al arrancar. Hace tres cosas, **en este orden**:

1. Se suscribe a las respuestas.
2. Pregunta por su estado (`/get`).
3. Reporta lo que es.

> ### La regla de oro
>
> **Suscríbete a las respuestas ANTES de publicar la petición.** Si publicas
> en `/get` y te suscribes después a `/get/accepted`, la respuesta de AWS ya
> pasó y no la vas a ver nunca. El programa se queda esperando algo que ya
> ocurrió, sin ningún error que lo explique.
>
> **Y la versión fina, que es la que de verdad muerde:** no basta con
> *llamar* a `subscribe()`; hay que esperar a que AWS **confirme** la
> suscripción. `subscribe()` solo deja la petición en camino. Si publicas el
> `/get` en la línea siguiente, AWS puede resolver tu consulta y mandar la
> respuesta antes de haber terminado de registrarte: sale al topic, no hay
> nadie escuchando, y se pierde.
>
> Por eso en `shadow_dispositivo.py` el `/get` **no** se publica dentro de
> `al_conectar()`, sino dentro de `al_suscribir()`, cuando están confirmadas
> las cinco suscripciones. Este laboratorio se escribió primero de la forma
> ingenua, y el síntoma fue exactamente el descrito: conectado, sin errores,
> esperando para siempre.

Ahora míralo en la consola: **IoT Core → Administrar → Objetos → tu objeto →
pestaña *Device Shadows* → *Classic Shadow***. Ahí está el JSON que acaba de
escribir tu computadora.

### Dale una orden desde la consola

En esa misma pantalla, **Editar** el documento y poner:

```json
{
  "state": {
    "desired": { "bomba": "encendida" }
  }
}
```

Guarda y mira la terminal del dispositivo. Recibió el delta, «encendió» la
bomba y reportó. Refresca la consola: `desired` y `reported` coinciden, y el
delta desapareció.

**Nadie le mandó un mensaje al programa.** El programa preguntó qué debía
ser, y AWS se lo dijo.

---

## Paso 5 · El dispositivo apagado

Aquí es donde se cierra el círculo.

1. `Ctrl + C` en la terminal del dispositivo. Se apagó.
2. En la consola, cambia `desired` a `{"bomba": "apagada"}`. Guarda.
   **No pasa nada: nadie está escuchando.** Pero la orden quedó escrita.
3. Vuelve a arrancar el dispositivo.

**Obedece**, sin que nadie repita la orden. Porque al arrancar lo primero que
hace es preguntar.

Compáralo con el laboratorio 03: allí, un comando enviado con el programa
apagado desaparecía. Aquí no, y el cambio no está en la red ni en el
protocolo. Está en **qué mandamos**: antes mandábamos órdenes, ahora
declaramos estados.

---

## Paso 6 · La aplicación da la orden

Hasta ahora las órdenes salían de la consola de AWS. En la vida real salen de
un programa. Abre **una segunda terminal** y deja el dispositivo corriendo en
la primera.

```bash
docker compose run --rm app python shadow_app.py ver
docker compose run --rm app python shadow_app.py encender
docker compose run --rm app python shadow_app.py umbral 60
docker compose run --rm app python shadow_app.py apagar
```

Dos terminales, lado a lado. La de la izquierda es un **dispositivo** que
entró con un certificado. La de la derecha es una **aplicación** que entró
con claves. Ninguna de las dos sabe que la otra existe: se comunican a través
del estado.

Pruébalo también con el dispositivo apagado: la aplicación no se entera y no
le importa. Deja la orden escrita y termina.

---

## Cuándo NO usar un shadow

Esto separa a quien entendió de quien copió los comandos.

| Usa **shadow** para... | Usa un **topic normal** para... |
|---|---|
| **Estado**: encendido/apagado, umbral, modo, versión de firmware | **Telemetría**: temperatura cada 5 segundos |
| Algo que te importa **ahora mismo** | Algo que te importa como **serie histórica** |
| Pocos cambios, que deben persistir | Muchos mensajes, que fluyen |

Tres razones concretas:

- **Tamaño.** El documento tiene un límite de **8 KB** (solo cuentan `desired`
  y `reported`; la metadata que añade AWS no). Una serie temporal no cabe.
- **Costo.** Las operaciones de shadow se cobran **por cada 1 KB**: una
  actualización de 1,5 KB cuenta como dos. Meter telemetría ahí multiplica la
  factura sin aportar nada.
- **Semántica.** El shadow guarda **el último valor**, no la historia. Si
  publicas cien temperaturas, el shadow tiene una. Lo que quieres guardar va
  a una base de datos.

---

## Errores comunes

| Lo que ves | Qué pasa |
|---|---|
| La conexión se corta al arrancar | La política no cubre `$aws/things/.../shadow/*`. Paso 1 |
| Guardaste la política y sigue igual | No marcaste «establecer como versión activa» |
| El dispositivo no recibe nada | Te suscribiste después de publicar. Regla de oro, paso 4 |
| `ResourceNotFoundException` | El shadow no existe aún: arranca el dispositivo primero |
| `AccessDeniedException` en la app | Al usuario de IAM le falta `iot:UpdateThingShadow` |
| `UnrecognizedClientException` | Copiaste la clave incompleta, o la borraste en IAM |
| Un `409` al actualizar | Alguien escribió antes que tú; tu número de versión ya estaba viejo |

---

## Lo que queda en tu cuenta

Un shadow por objeto. No cuesta nada tenerlo ahí y lo vamos a usar en las
clases siguientes, así que **no lo borres**.

Si quieres dejar de usar la clave de acceso de IAM, puedes desactivarla desde
la consola y volver a activarla cuando la necesites. Es buena costumbre con
cualquier credencial que no estés usando.

---

## Reto opcional: el mismo ciclo en un ESP32

Mismo shadow, misma política, pero el que obedece es la placa: un LED que se
enciende desde la consola de AWS **aunque la placa estuviera apagada cuando
diste la orden**.

Está en `esp32/`. Es la continuación del reto del laboratorio 03.

---

## Seguridad: lo que nunca se sube

El archivo `.env` de esta carpeta (claves de IAM), la carpeta `certificados/`
del laboratorio 03 y los `mi-politica*.json` generados están excluidos del
repositorio a propósito.

Si alguna vez publicas una clave de acceso por error —pasa más de lo que
parece—, entra a IAM y **bórrala inmediatamente**. Crear una nueva toma treinta
segundos; que alguien use la tuya para minar criptomonedas en tu cuenta, no.
