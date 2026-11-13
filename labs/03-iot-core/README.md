# Laboratorio 03 — Tu primer dispositivo en AWS IoT Core

Al terminar, **tu computadora le va a mandar datos a Amazon** y tú vas a ver
llegar cada mensaje en la consola de AWS. Con tu cuenta y con un certificado
que solo tú tienes.

No necesitas saber nada de AWS para seguir esta guía, y **no necesitas
instalar Python**: Docker se encarga.

---

## Antes de empezar

- **Docker Desktop** corriendo (lo usaste en el laboratorio 02).
- **Cuenta de AWS** activa.
- **Saber en qué región estás.** Las cuentas nuevas abren la consola en una
  región fija —suele ser `Ohio (us-east-2)`— y **no muestran selector de
  región**. No intentes cambiarla: usa la que te toque, **anótala**, y
  asegúrate de que todo lo que crees esté en esa misma. La región va dentro
  de tu endpoint, así que si algún día «desaparecen» tus cosas, es que estás
  mirando otra.

---

## Paso 0 · Protege tu cuenta antes de crear nada

Dos minutos que te ahorran disgustos. Hazlos **antes** de seguir.

### Tu alerta de gasto

Las cuentas nuevas traen créditos que **expiran a los seis meses**, y nada
avisa si algo se queda encendido consumiéndolos.

1. Buscador → **Administración de facturación y costos** → **Presupuestos**.
2. **Crear presupuestos** → plantilla **«Presupuesto de gasto cero»**.
3. Ponle un nombre (`alerta-de-gasto`) y **tu correo**. Crear.

Te avisará en cuanto el gasto supere **0,01 USD**. No corta nada —AWS no tiene
un botón de «no gastes más de X»— pero te enteras el mismo día en vez de a fin
de mes.

> Verás que la dirección cambia a `us-east-1` aunque tu consola esté en otra
> región: la facturación es un servicio global. Es normal.

### No trabajes con la cuenta raíz

La cuenta con la que te registraste —la **raíz**— lo puede todo: borrar la
cuenta, cambiar la tarjeta, cerrar servicios. Está atada a tu medio de pago.
La buena práctica, en cualquier nube, es la misma: **identidades separadas y
permisos mínimos**, y la raíz reservada para lo imprescindible.

Lo mínimo que debes hacer hoy: **activa MFA en la cuenta raíz**
(tu nombre → *Security credentials*).

Y una advertencia, porque los tutoriales viejos dicen otra cosa: si entras a
**IAM → Usuarios**, la propia consola te avisa de que **los usuarios de IAM
son solo para acceso programático**, y que a las personas se las invita desde
la página del equipo. Al crear uno verás *«Tipo de contraseña de consola:
None»*: no puede entrar a la consola.

> Guárdate esta idea, porque es la misma que usarás en este laboratorio:
> **un usuario de IAM es a un programa lo que el certificado X.509 es a tu
> dispositivo.** Identidades de máquina, no de persona.

## Paso 1 · Crear tu dispositivo en AWS

1. En el buscador de la consola, escribe **IoT Core** y entra.
   *(Dale a la estrella para dejarlo en favoritos: lo vas a usar varias veces.)*
2. En el menú de la izquierda: **Connect** → **Connect one device**.
3. El asistente te pregunta el nombre del dispositivo. **Usa tu nombre**, por
   ejemplo `cesar-01`. Nada de `test` ni `prueba`: en la clase va a haber
   veinte dispositivos y hay que distinguirlos.
4. Sigue el asistente hasta que te ofrezca descargar el **connection kit**.

> El asistente crea tres cosas a la vez, y conviene saberlo: el **Thing** (la
> ficha de tu dispositivo), un **certificado** (su identidad) y una
> **política** (lo que tiene permitido hacer).

## Paso 2 · Guardar los certificados — el paso crítico

**Antes de darle a descargar**, crea la carpeta donde van a vivir. Es la
carpeta `certificados` que está junto a este archivo:

```
labs/03-iot-core/certificados/
```

> ### La llave privada se descarga UNA sola vez
>
> AWS no la guarda. Si cierras esa ventana sin bajarla, **no hay forma de
> recuperarla**: hay que crear un certificado nuevo. No es grave —son dos
> minutos— pero es mejor no pasar por ahí.

Descomprime el kit dentro de esa carpeta. Debes terminar con tres archivos:

| Archivo | Qué es |
|---|---|
| `xxxxx-certificate.pem.crt` | Tu certificado: dice quién eres |
| `xxxxx-private.pem.key` | Tu llave privada: **no la compartas nunca** |
| `AmazonRootCA1.pem` | Con esto compruebas que el servidor es de verdad Amazon |

Si el kit no trae la Root CA, bájala de
<https://www.amazontrust.com/repository/AmazonRootCA1.pem> y ponla ahí.

**Haz una copia** de esa carpeta en un USB o en tu nube personal. La necesitas
en las clases siguientes.

## Paso 3 · Decirle al programa dónde está tu cuenta

Cada cuenta de AWS tiene su propia dirección. En la consola:
**IoT Core** → menú izquierdo abajo → **Settings** → copia el
**Device data endpoint**. Se parece a esto:

```
a1b2c3d4e5f6g7-ats.iot.us-east-1.amazonaws.com
```

Copia el archivo de ejemplo y escribe ahí tu endpoint y el nombre de tu Thing:

```bash
cp .env.example .env
```

```powershell
Copy-Item .env.example .env
```

```ini
AWS_IOT_ENDPOINT=a1b2c3d4e5f6g7-ats.iot.us-east-1.amazonaws.com
DISPOSITIVO_ID=cesar-01
```

## Paso 4 · Comprobar que todo está en su sitio

Antes de intentar nada, pregúntale al comprobador:

```bash
docker compose run --rm aws python comprobar.py
```

Revisa seis cosas en orden —los tres archivos, tu endpoint, que exista, que tu
red deje pasar el puerto 8883, que AWS te reconozca y que te deje publicar— y
te dice **exactamente** qué falta en cada caso.

**No sigas hasta que todo salga en verde.**

## Paso 5 · Darle permisos a tu dispositivo

La primera vez, el comprobador va a fallar en el paso 5 con un mensaje como
*«AWS aceptó el cifrado pero cortó la conexión sin responder»*. **No es un
error tuyo.**

La política que crea el asistente solo autoriza los topics de su propio
ejemplo (`sdk/test/...`) y unos nombres de cliente fijos. Con tu dispositivo y
tus topics, AWS rechaza la conexión — y, como verás, **no dice por qué**:
simplemente cuelga. Reconocer ese silencio es media clase de seguridad en IoT.

Para arreglarlo:

1. Consola → **Security** → **Policies** → tu política → **Edit** (o *Editar
   versión activa*).
2. Cambia el editor de **Creador** a **JSON**.
3. Borra lo que hay y pega el contenido de **`politica-curso.json`**, que está
   en esta carpeta, sustituyendo `REGION` por la tuya y `CUENTA` por el número
   de tu cuenta (lo ves en el ARN que muestra la misma pantalla).
4. Marca **«establecer como versión activa»** antes de guardar, o la versión
   nueva no se aplica a nada.
5. Vuelve a ejecutar el comprobador. Ahora sí: todo en verde.

Esa política dice exactamente tres cosas: que este certificado puede
conectarse **con el nombre de su propio objeto**, y publicar y suscribirse
**solo en `fablab/planta1/…`**. Eso es el mínimo privilegio: si alguien robara
el certificado, no podría tocar los topics de los demás.

## Paso 6 · Publicar, y verlo llegar

Abre dos cosas a la vez.

**En la consola de AWS:** **IoT Core** → **Test** → **MQTT test client** →
pestaña *Subscribe to a topic* → escribe `fablab/#` → **Subscribe**.

**En tu terminal:**

```bash
docker compose run --rm aws python publicar.py
```

Mira la consola: tus mensajes van apareciendo. Eso que estás viendo salió de
tu computadora, viajó cifrado hasta un centro de datos de Amazon y volvió a tu
pantalla. **Ya tienes un dispositivo en la nube.**

Para detenerlo: `Ctrl + C`.

## Paso 7 · Recibir un comando

Ahora al revés. En la terminal:

```bash
docker compose run --rm aws python suscribir.py
```

Y en la consola de AWS, en el MQTT test client, pestaña
*Publish to a topic*:

- Topic: `fablab/planta1/TU-ID/comandos`
- Mensaje: `3`

Llega al instante, sin que tu programa haya preguntado nada. Es el mismo
*push* del laboratorio anterior, ahora contra AWS.

> **No ejecutes `publicar.py` y `suscribir.py` a la vez.** Los dos se
> identifican con el mismo nombre y el broker expulsa a uno de los dos.

---

## Lo que cambió respecto al laboratorio 02

Abre `publicar.py` y compáralo con el de la clase pasada. Son **tres
cambios**, marcados con `NUEVO` en el código:

| | Laboratorio 02 | Aquí |
|---|---|---|
| Dirección | `localhost` | el endpoint de tu cuenta |
| Puerto | `1883` | `8883` (en AWS no hay puerto sin cifrar) |
| Identidad | ninguna | `tls_set(...)` con tus tres archivos |

El `publish`, el topic y el payload son **idénticos**. Eso es lo que significa
que MQTT sea un estándar: tu código no sabe ni le importa si al otro lado hay
un Mosquitto en tu laptop o la infraestructura de Amazon.

---

## Los permisos, en la práctica

La política que creó el asistente dice qué puede hacer tu certificado.
Pruébalo rompiéndola a propósito:

1. **Security** → **Policies** → tu política → **Edit**.
2. Quita la acción `iot:Publish` y guarda.
3. Ejecuta `publicar.py` otra vez.

**Falla** — y fíjate en algo importante: el error no dice «te falta un
permiso». La conexión simplemente se corta. Así se ve en producción, y por eso
conviene reconocerlo hoy.

Devuélvelo, pero apuntando solo a **tu** topic en vez de a `*`. A eso se le
llama **mínimo privilegio**: si alguien roba ese certificado, solo puede
escribir en el topic de ese dispositivo, no en los de toda la flota.

---

## Errores comunes

| Lo que ves | Qué pasa |
|---|---|
| El comprobador no encuentra los archivos | Están en Descargas, no en `certificados/`, o sin descomprimir |
| `no se puede abrir el puerto 8883` | Tu red lo bloquea. Prueba compartiendo datos del teléfono |
| AWS rechaza la conexión | El certificado no está *Active*, o no tiene política o Thing adjuntos |
| Conecta pero no publica | La política no permite `iot:Publish` en ese topic |
| No veo nada en el MQTT test client | Te suscribiste a otro topic, o estás en otra región |
| Mi Thing desapareció | Estás mirando otra región. Revisa el selector de arriba a la derecha |

---

## Reto opcional: el mismo dispositivo, en un ESP32

En `esp32/aws_iot_esp32/` tienes el sketch. Es el de la clase 2 con el puerto
8883 y tus certificados compilados dentro del programa — porque el ESP32 no
tiene dónde guardar archivos sueltos.

Eso crea un problema que no teníamos en Python: **si pegas la llave privada
en el `.ino`, la llave viaja con el código**. Y los `.ino` se comparten por
correo, por USB y por repositorio. Así que van en un archivo aparte, que se
genera solo:

```bash
docker compose run --rm aws python generar_secretos.py
```

Lee tu carpeta `certificados` y escribe `esp32/aws_iot_esp32/secretos.h` con
los tres certificados ya formateados. Abre el sketch en el IDE de Arduino:
`secretos.h` aparece como una pestaña al lado del `.ino`, y lo único que
escribes a mano es tu WiFi.

| Archivo | Qué lleva | ¿Se sube al repositorio? |
|---|---|---|
| `aws_iot_esp32.ino` | el programa | **sí** |
| `secretos.h` | tu WiFi, tu endpoint, tus certificados | **no** (está en el `.gitignore`) |
| `secretos.h.ejemplo` | la plantilla, con huecos | sí |

Trae una trampa que vale la pena conocer: el ESP32 **necesita saber la fecha**.
Un certificado tiene periodo de validez, así que si el reloj del chip está en
1970, AWS rechaza la conexión sin más explicación. Por eso el sketch
sincroniza la hora por NTP antes de conectarse.

Es para hacer en casa, con calma. Si lo logras, tráelo a la clase siguiente.

---

## Seguridad: lo que nunca se sube

La carpeta `certificados/` y el archivo `.env` están excluidos del
repositorio a propósito. **Tu llave privada es como la contraseña de tu
cuenta**: quien la tenga puede hacerse pasar por tu dispositivo.

Si alguna vez la publicas por error —pasa más de lo que parece—, entra a la
consola, desactiva ese certificado y crea uno nuevo. Es gratis y toma dos
minutos.
