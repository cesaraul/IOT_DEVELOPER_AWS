# Laboratorio 05 — Rules Engine y Lambda

> 📊 **Diapositivas de la clase:**
> [Rules Engine y Lambda](../../docs/clases/clase-05-rules-engine-y-lambda.pdf)

En la clase 4 tu dispositivo quedó publicando nivel y temperatura, y gritando
`"alarma": true` cuando se pasa del umbral. **Pero nadie lo escucha.** Ese
aviso se queda en una pestaña de pruebas que cierras al rato.

Hasta ahora, para que algo reaccionara tenías que dejar un `suscribir.py`
abierto en una terminal para siempre. Hoy eso se acaba: le dejas escrita a
AWS una **regla** —qué mensajes te importan y qué hacer con ellos— y AWS la
ejecuta sola, siempre, sin ningún programa tuyo encendido.

---

## Cómo está repartido este laboratorio

| | Qué |
|---|---|
| **Antes de AWS** | El [simulador](simulador/), en tu laptop. Armas la regla con bloques y ves qué le pasa a cada mensaje. Gratis y sin riesgo |
| **En clase** | Pasos 0 a 6: tu primera regla de verdad, y una Lambda que te enseña qué le llega |
| **En casa** | Pasos 7 a 11: que esa Lambda te mande un correo cuando haya alarma |

Los pasos 7 a 11 son **tuyos**, para terminar fuera del aula. Están escritos
con el mismo detalle, y al final hay una tabla de errores comunes con todo
lo que ya nos pasó a nosotros montándolo.

---

## Antes de empezar

Necesitas el **laboratorio 04 funcionando**. Este reutiliza su dispositivo,
sus certificados y su `.env`: no hay que crear nada nuevo en AWS.

```bash
cd ../04-device-shadow
```

```bash
docker compose run --rm dispositivo python comprobar.py
```

Si no sale todo en verde, arregla eso primero.

---

# En clase

## Paso 0 · Preparar el terreno

Baja el ritmo del dispositivo. Vas a mirar mensajes uno por uno, y a dos
segundos no se lee nada:

```bash
docker compose run --rm app python shadow_app.py intervalo 10
```

> Fíjate en lo que acabas de hacer: **usaste el shadow de la clase pasada
> para configurar el equipo.** Eso ya es parte de la clase de hoy.

Y arranca el dispositivo, que es la fuente de datos de todo el día. Déjalo
corriendo en su terminal:

```bash
docker compose run --rm dispositivo python shadow_dispositivo.py
```

## Paso 1 · Ver el punto de partida

Consola → **IoT Core** → **Probar** → **Cliente de prueba de MQTT** →
pestaña *Suscribirse a un tema* → escribe `fablab/#` → **Suscribirse**.

Ahí están tus datos llegando. **Y no le pasa nada a nadie.** Ese es el
problema que vamos a resolver.

## Paso 2 · Tu primera regla: republicar

Esta regla no manda correos ni llama a nada: solo mueve el mensaje a otro
topic. Por eso es la primera — **se ve al instante y no puede costar nada**.

1. **IoT Core** → menú izquierdo → **Enrutamiento de mensajes** → **Reglas**
   → **Crear regla**.
2. Nombre: `alarmas_a_otro_topic`.
   > Solo letras, números y guion bajo. **Los guiones normales no se
   > admiten** y el error aparece recién al final del asistente.
3. **Siguiente**. En **Instrucción de SQL**, borra lo que haya y pega:

```sql
SELECT nivel, temp FROM 'fablab/planta1/+/telemetria' WHERE alarma = true
```

4. **Siguiente** → **Acción de regla 1** → **Republicar en tema de AWS IoT**.
5. Tema: `fablab/alarmas`.
6. **Rol de IAM** → **Crear nuevo rol** → nombre `rol-regla-iot` → **Crear**.

> **Páralo aquí treinta segundos.** Este es el **tercer tipo de identidad**
> del curso. No es un dispositivo ni una persona: es **AWS actuando en tu
> nombre**.
>
> | Quién | Se identifica con | Lo viste en |
> |---|---|---|
> | Un dispositivo | certificado X.509 | clase 3 |
> | Una persona o aplicación | usuario de IAM | clase 4 |
> | **Un servicio de AWS** | **rol de IAM** | **hoy** |

7. **Siguiente** → **Crear**.

## Paso 3 · Verla funcionar

Vuelve al **Cliente de prueba de MQTT** y suscríbete también a
`fablab/alarmas`.

Cuando el nivel de tu tanque pase del umbral, empiezan a aparecer mensajes
ahí:

```json
{"nivel": 91.2, "temp": 28.4}
```

**Fíjate en lo que falta: `alarma` no está.** Se usó para *decidir*, no para
*llevárselo*. Eso es lo que hace el `SELECT`. Si quieres el mensaje entero,
sería `SELECT *`.

Ahora apaga la bomba desde la otra terminal:

```bash
docker compose run --rm app python shadow_app.py apagar
```

El nivel baja, la alarma se apaga, y **a `fablab/alarmas` deja de llegar
nada**. La regla sigue ahí, evaluando cada mensaje y descartándolos todos en
silencio.

## Paso 4 · Crear la Lambda

1. Buscador → **Lambda** → **Crear función**.
2. Nombre: `alarma_tanque`.
3. **Versión ejecutable**: **Python 3.13**.
   > No elijas 3.9 ni 3.10 aunque aparezcan en tutoriales viejos: están
   > retirados y no se pueden crear.
4. Despliega **Configuración adicional** → **Rol de ejecución** → **Crear un
   rol nuevo con permisos básicos de Lambda**.
5. Si te ofrece una **Política adicional**, elige **«No hay políticas
   adicionales»**.
6. **Crear función**.

> El punto 4 sostiene media clase. Ese rol nace sabiendo **una sola cosa**:
> escribir sus propios registros. Nada más. En el paso 8 vas a ver qué pasa
> cuando intenta hacer algo que no tiene permitido — y ese error es el
> contenido, no un accidente.

En el editor de código, **borra todo** y pega:

```python
import json

def lambda_handler(event, context):
    print(json.dumps(event))
    return {"ok": True}
```

> **Borra todo de verdad.** La consola trae un ejemplo con
> `'Hello from Lambda!'`. Si pegas debajo sin borrar, quedan dos funciones
> `lambda_handler` en el mismo archivo: funciona de milagro y es ilegible.

Botón **Deploy**. Sin eso el código no se guarda.

> Esta función **no hace nada útil, a propósito**. Primero montamos el canal
> completo y comprobamos que el dato llega; la lógica viene después. Una
> función que intenta trabajar a la primera y falla te deja sin saber si el
> problema fue la regla, el permiso, el evento o tu código.

## Paso 5 · Conectar la regla con la Lambda

1. **IoT Core** → **Enrutamiento de mensajes** → **Reglas** →
   `alarmas_a_otro_topic` → **Editar**.
2. **Agregar acción de regla** → **Lambda** → elige `alarma_tanque`.
3. **Guardar**.

> Al añadir la acción desde aquí, la consola le concede a la regla el permiso
> para invocar tu función. Ese permiso **vive en la función**, no en la
> regla. Acuérdate de esto: está en la tabla de errores comunes y es el fallo
> más difícil de ver de todo el laboratorio.

## Paso 6 · Ver qué le llegó

Ese `print` no sale en ninguna pantalla: va a los registros. Y se llega
**desde la propia función**:

> **Lambda** → `alarma_tanque` → pestaña **Monitor** → **Ver registros de
> CloudWatch** → entra en el flujo más reciente.

Vas a ver cinco líneas por cada ejecución:

| Línea | Qué es |
|---|---|
| `INIT_START Runtime Version: python:3.13` | AWS **creó el contenedor** desde cero |
| `START RequestId: …` | Empieza una ejecución |
| `{"nivel": 91.2, "temp": 28.4}` | **Tu `print`** |
| `END RequestId: …` | Terminó |
| `REPORT … Duration … Billed Duration` | Lo que duró y lo que se cobra |

**Dos cosas que mirar antes de cerrar:**

- En el JSON **no está `alarma`** — exactamente lo que eligió tu `SELECT`.
- Deja llegar otro mensaje y refresca: habrá un `START` **sin `INIT_START`
  delante**. AWS reutilizó el contenedor. Guárdate ese detalle; en el paso 10
  explica algo importante.

**Hasta aquí llegamos en clase.** Ya tienes el canal completo: dispositivo →
regla → función → registros.

---

# En casa

Lo que sigue hace que esa función sirva para algo: **que te avise por correo
cuando el tanque se desborde.**

## Paso 7 · Crear el tema de correo

1. Buscador → **Simple Notification Service** (SNS).
2. Menú izquierdo → **Temas** → **Crear tema**.
3. Tipo: **Estándar**.
   > **No se puede cambiar después**, y un tema FIFO **no admite correo**.
4. Nombre: `alarmas-tanque`.
5. **Nombre para mostrar**: `Tanque FabLab`. Es el remitente que verás en tus
   correos de alarma.
6. Todo lo demás, por defecto. **Crear tema**.
7. Dentro del tema → pestaña **Suscripciones** → **Crear suscripción**.
8. Protocolo: **Correo electrónico**. Punto de enlace: **tu correo**.
   **Crear suscripción**.
9. **Ve a tu correo y confirma el enlace.** Hasta que lo hagas, el estado
   dice *Pendiente de confirmación* y no llega nada. Mira en spam.

> El correo de confirmación llega siempre de *«AWS Notifications»*, aunque
> hayas puesto nombre para mostrar. El tuyo aparece a partir del segundo.

10. Copia el **ARN del tema**, arriba en la página. Lo necesitas en el paso
    siguiente. Se parece a:
    `arn:aws:sns:us-east-2:123456789012:alarmas-tanque`

## Paso 8 · Preparar la función

### 8.1 · La variable de entorno — primero

**Lambda** → `alarma_tanque` → **Configuración** → **Variables de entorno** →
**Editar** → **Agregar**:

- Clave: `TEMA_SNS`
- Valor: el ARN que copiaste

**Guardar**.

> Esto va **antes** que el código. Si lo haces al revés, la función ni
> arranca: revienta con `KeyError: 'TEMA_SNS'` antes de ejecutar una línea
> tuya, y el error parece un fallo de programación.

### 8.2 · Más tiempo

**Configuración general** → **Editar** → tiempo de espera: **10 segundos**.

> No cuesta nada: se paga por milisegundo **usado**, no por el límite.

### 8.3 · El código

Pestaña **Código**, **borra todo** y pega:

```python
import os

import boto3

sns = boto3.client("sns")
TEMA = os.environ["TEMA_SNS"]

# Vive entre ejecuciones: AWS reutiliza el mismo contenedor un rato.
# Es memoria frágil — no sirve para nada serio — pero alcanza para no
# mandar 300 correos, que es justo lo que la regla no sabía hacer.
avisado = False


def lambda_handler(event, context):
    global avisado

    if avisado:
        print("ya avisé, no repito")
        return

    avisado = True
    sns.publish(
        TopicArn=TEMA,
        Subject="Alarma en el tanque",
        Message=f"Nivel {event.get('nivel')} — temperatura {event.get('temp')}",
    )
    print("correo enviado")
```

**Deploy**.

## Paso 9 · Verla fallar

Enciende la bomba y espera a que salte la alarma:

```bash
docker compose run --rm app python shadow_app.py encender
```

Mira los registros. **Tiene que fallar**, y así:

```
AccessDeniedException: User: arn:aws:sts::…:assumed-role/alarma_tanque-role-…
is not authorized to perform: SNS:Publish on resource: arn:aws:sns:…
```

Léelo entero. Dice tres cosas:

- **Quién** no tiene permiso: el **rol de tu función**, no tú.
- **Qué** intentaba: `SNS:Publish`.
- **Sobre qué**: tu tema.

> Y el contraste que vale todo el curso: **esta vez AWS sí te lo dijo.**
> Cuando a un dispositivo le falta un permiso en IoT, la conexión se corta en
> silencio — lo sufriste en las clases 3, 4 y 5. En IAM te dan el quién, el
> qué y el sobre qué.

## Paso 10 · Darle el permiso, y solo ese

1. **Configuración** → **Permisos** → clic en el **nombre del rol** (abre
   IAM en otra pestaña).
2. **Agregar permisos** → **Crear política insertada** → pestaña **JSON**.
3. Borra lo que haya y pega esto, **con tu ARN**:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:us-east-2:123456789012:alarmas-tanque"
  }]
}
```

4. **Siguiente** → nombre: `puede-avisar` → **Crear política**.

> **Por qué el rodeo hasta IAM:** el permiso no vive en Lambda. La pestaña
> *Permisos* es una ventana de consulta —te dice con qué identidad corre tu
> función— y el nombre del rol es un atajo a donde sí se edita.
>
> Es la misma estructura de la clase 3 con otros nombres: el **certificado**
> dice quién es el dispositivo y la **política** adjunta dice qué puede
> hacer; el **rol** dice quién es la función y la **política** adjunta dice
> qué puede hacer.

Una acción, un recurso: esa función puede mandar correos **a ese tema** y
nada más en toda tu cuenta de AWS.

## Paso 11 · La prueba

No hay que tocar la función: el permiso se aplica solo. Espera al siguiente
mensaje de alarma.

**Te van a llegar dos correos, no uno.** Y eso no es un fallo:

> AWS creó **dos contenedores** para tu función, y cada uno arrancó con su
> propio `avisado = False`. ¿Te acuerdas del `INIT_START` del paso 6?
> Apareció dos veces.
>
> La variable global sobrevive entre invocaciones del **mismo** contenedor,
> pero no entre contenedores distintos. O sea: el truco bajó de **300 correos
> a 2**. Resuelve el problema práctico, pero **no es memoria de verdad**.
>
> ¿Dónde iría ese estado para que fuera fiable? En una base de datos. **Y eso
> es la clase 6.**

En los registros se ve clavado: `correo enviado` dos veces, y
`ya avisé, no repito` en todas las demás ejecuciones.

## Paso 12 · Apagar antes de cerrar la laptop

1. **Para el dispositivo** (`Ctrl + C`). Sin datos no hay reglas ni correos.
2. **IoT Core → Reglas →** tu regla → **Desactivar**. Queda guardada para la
   clase siguiente, pero no se dispara.
3. **Borra las reglas de prueba** que hayas creado por el camino.

> Una regla olvidada **no se nota**: no da error, solo gasta. Es la versión
> en la nube de dejar la luz encendida — y para eso pusimos la alerta de
> presupuesto el primer día.

La función y el tema de SNS **no cuestan nada mientras nadie los llame**. Lo
que cuesta es un dispositivo publicando sin que nadie lo mire.

---

## Errores comunes

Todos estos nos pasaron montando el laboratorio. No son hipotéticos.

| Lo que ves | Qué pasa |
|---|---|
| La regla se ve bien, pero **la función nunca se ejecuta** y no hay nada en sus registros | Al borrar y volver a crear la función **se perdió el permiso de invocación**. Vive en la función, no en la regla. Edita la regla, **quita la acción Lambda y vuelve a agregarla** |
| `KeyError: 'TEMA_SNS'` | Desplegaste el código antes de crear la variable de entorno. Paso 8.1 |
| `AccessDeniedException … SNS:Publish` | Falta el permiso del paso 10. **Es lo esperado la primera vez** |
| `'Hello from Lambda!'` mezclado con tu código | No borraste el ejemplo antes de pegar. Quedan dos `lambda_handler` |
| El nombre de la regla no se acepta | Lleva guiones normales. Solo letras, números y guion bajo |
| Llegan mensajes a `fablab/alarmas` **sin alarma** | Tienes otra regla con `WHERE alarma = false`. Búscala y desactívala |
| No llega ningún correo | La suscripción sigue en *Pendiente de confirmación*. Revisa tu correo y el spam |
| El correo llega de «AWS Notifications» | Es el de confirmación. El nombre que pusiste aparece en los siguientes |
| El rol se llama `PowerUserRole` o parecido | No elegiste «crear un rol nuevo» al crear la función. Cámbialo en *Configuración → Permisos → Editar* |

---

## Lo que cuesta

| Servicio | Gratis | Después |
|---|---|---|
| Reglas de IoT | ~250.000 reglas disparadas al mes | 0,15 USD por millón |
| Lambda | 1 millón de invocaciones al mes, **permanente** | céntimos |
| SNS por correo | **1.000 correos al mes**, y no caduca | ~2 USD por cada 100.000 |

> **Ojo con una cosa.** Si pusieras la acción de correo **en la regla** en
> vez de en la función, con tu equipo publicando cada 2 segundos te comerías
> los 1.000 correos gratis en media hora — y tu bandeja de entrada con
> ellos. Por eso el correo lo manda la Lambda que recuerda, y por eso la
> tormenta de alertas se vive en el [simulador](simulador/), que es local y
> gratis.
