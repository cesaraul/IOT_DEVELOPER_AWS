# Montarlo todo con un agente

Todo lo que construiste a mano en las clases 3 a 6 se puede montar con la
**línea de comandos de AWS**. Y un agente —Claude, ChatGPT— sabe escribir
esos comandos.

Esta guía son los **prompts**, en orden, para que lo haga por ti.

---

## Antes de nada: esto no sustituye las clases

> **Si no hubieras hecho los laboratorios, esta guía sería peligrosa.**

Un agente va a crear en dos minutos lo que a ti te costó cuatro clases. El
problema no es que se equivoque: es que **si no sabes qué debería haber
hecho, no vas a notar que se equivocó.**

Cuando te diga «listo, la regla está creada», tú tienes que poder preguntarte:
¿con qué `SELECT`? ¿con `WHERE` o sin él? ¿qué rol le puso? ¿ese rol qué
permisos tiene? Eso lo sabes **porque lo hiciste a mano primero**.

El valor de un agente no es que sepa más que tú. Es que escribe más rápido lo
que tú ya sabes revisar.

---

## Qué necesitas

### 1. Tu usuario y tus claves

Las del documento [Conectar tu laptop a AWS](acceso-desde-tu-laptop.md).

### 2. Saber qué tipo de agente tienes delante

| | Qué puede hacer | Cómo trabajas |
|---|---|---|
| **Agente con terminal** (Claude Code, Codex, Gemini CLI…) | Ejecuta los comandos él mismo | Le das el objetivo y él actúa |
| **Chat** (claude.ai, chatgpt.com) | **Solo escribe** los comandos | Él te los da, tú los pegas en tu terminal |

Las dos formas sirven. Los prompts son los mismos; lo que cambia es quién
pulsa Enter.

> ### 🔴 Nunca pegues tu clave secreta en una ventana de chat
>
> Ni para que «la configure por ti». Un agente con terminal **lee las
> credenciales del sistema** y nunca necesita verlas. Un chat no las necesita
> en absoluto: él escribe el comando y tú lo ejecutas con tus credenciales ya
> puestas.
>
> Si alguna vez un asistente te pide la clave secreta, la respuesta es no.

### 3. El AWS CLI configurado

Instala el [AWS CLI](https://aws.amazon.com/cli/) y configúralo una vez:

```bash
aws configure
```

Te pedirá cuatro cosas: el **id de clave de acceso**, la **clave secreta**,
la **región** (la tuya, por ejemplo `us-east-2`) y el formato (`json`).

Comprueba que funciona:

```bash
aws sts get-caller-identity
```

Si te devuelve tu número de cuenta y el ARN de tu usuario, ya está.

---

## Paso 0 · Las reglas de la casa

**Este es el prompt más importante de todos.** Dáselo antes que ningún otro,
en la misma conversación.

Tus claves tienen acceso total a tu cuenta. Sin reglas, un malentendido se
puede llevar por delante lo que ya tienes montado.

```
Vas a ayudarme a montar un laboratorio de IoT en MI cuenta de AWS, usando el
AWS CLI que ya está configurado en esta máquina.

Reglas que no puedes saltarte:
1. Trabaja SOLO en la región us-east-2.
2. Antes de ejecutar cualquier comando que CREE, MODIFIQUE o BORRE algo,
   enséñamelo y espera a que yo diga que sí.
3. No borres nada que no hayas creado tú en esta conversación.
4. Ponle a todo lo que crees el prefijo "lab-" en el nombre, para que yo
   pueda distinguirlo del resto.
5. Si un recurso puede generar costo, dímelo antes de crearlo y dame una
   estimación.
6. Al final de cada paso, dime cómo COMPROBAR que salió bien, con un comando
   de solo lectura que pueda ejecutar yo.

Empieza confirmando con qué identidad estás trabajando y en qué región.
```

> La regla 2 es la que importa. Un agente que te enseña el comando antes de
> ejecutarlo es un agente del que puedes aprender; uno que actúa solo es una
> caja negra.

---

## Paso 1 · El dispositivo (lo de la clase 3)

```
Crea un dispositivo de IoT completo en mi cuenta:

- Un Thing llamado "lab-tanque-01".
- Un certificado X.509 nuevo, activo, y guárdame los archivos en la carpeta
  ./certificados de este proyecto: el certificado, la llave privada y el
  certificado raíz de Amazon.
- Una política llamada "lab-politica" que permita SOLO:
    * conectarse con el nombre del propio objeto
      (usa la variable ${iot:Connection.Thing.ThingName})
    * publicar y recibir en topic/fablab/planta1/*
    * suscribirse en topicfilter/fablab/planta1/*
- Adjunta la política al certificado y el certificado al Thing.
- Dime mi endpoint de datos de IoT.

Antes de crear nada, enséñame el JSON de la política y explícame qué permite
cada bloque.
```

**Qué revisar tú:** que la política use la variable `${iot:Connection.Thing.ThingName}`
y **no** el nombre del dispositivo escrito a mano. Si lo escribe a mano,
funciona — pero deja de servir para un segundo dispositivo, y eso es
exactamente lo que vimos en clase.

> **Ojo con la llave privada:** solo se puede descargar en el momento de
> crear el certificado. Si el agente no la guarda en ese momento, se pierde y
> hay que crear otro certificado. Compruébalo tú: el archivo tiene que
> existir y empezar por `-----BEGIN`.

## Paso 2 · El gemelo digital (lo de la clase 4)

```
Amplía la política "lab-politica" para que el dispositivo pueda usar su
Device Shadow: añade permiso de publicar, recibir y suscribirse en los topics
reservados $aws/things/${iot:Connection.Thing.ThingName}/shadow/*

Importante: crea una VERSIÓN NUEVA de la política y déjala como versión
ACTIVA. Enséñame el JSON completo antes.

Después, escribe el estado deseado del shadow de lab-tanque-01 con
{"bomba": "encendida"} y enséñame cómo queda el documento.
```

**Qué revisar tú:** que diga explícitamente que la versión quedó **activa**.
Es el fallo silencioso de la clase 4: se guarda una versión nueva que no se
aplica a nada.

## Paso 3 · La regla y la alerta (lo de la clase 5)

```
Monta la cadena de alertas:

1. Un tema de SNS llamado "lab-alarmas" y suscribe mi correo (te lo doy
   cuando me lo pidas). Avísame que tengo que confirmar el enlace.

2. Una función Lambda llamada "lab-alarma" en Python 3.13 que reciba el
   evento, lo imprima, y publique un aviso en ese tema de SNS solo la primera
   vez. El ARN del tema va en una variable de entorno, no escrito en el
   código.

3. Un rol de ejecución NUEVO para esa función, con los permisos mínimos:
   escribir sus propios registros y sns:Publish SOLO sobre ese tema.

4. Una regla de IoT llamada "lab_alarmas" con este SQL:
   SELECT nivel, temp FROM 'fablab/planta1/+/telemetria' WHERE alarma = true
   y dos acciones: republicar en fablab/alarmas, y llamar a la función.

5. Dale a la regla permiso para invocar la Lambda.

Explícame por qué el punto 5 hace falta y dónde vive ese permiso.
```

**Qué revisar tú:** el punto 5. Es el permiso que **vive en la función**, no
en la regla, y es el fallo más difícil de ver de todo el curso: la regla se
ve perfecta y la función nunca se ejecuta. Si el agente se lo salta,
pregúntaselo.

También revisa que el rol de la función tenga **solo** `sns:Publish` sobre tu
tema. Si le pone `AdministratorAccess` o `AmazonSNSFullAccess`, pídele que lo
apriete: ese es el ejercicio.

## Paso 4 · Guardar los datos (lo de la clase 6)

```
Monta el almacenamiento:

1. Una tabla de DynamoDB llamada "lab-telemetria" con clave de partición
   "dispositivo" (texto) y clave de ordenación "momento" (texto).
   Créala en modo APROVISIONADO con la capacidad mínima, para quedarme
   dentro del Free Tier. Explícame por qué eso importa.

2. Un bucket de S3 llamado "lab-telemetria-" seguido de mi número de cuenta,
   con el acceso público bloqueado.

3. Una regla de IoT llamada "lab_guardar" con
   SELECT *, topic(3) AS dispositivo, timestamp() AS momento
   FROM 'fablab/planta1/+/telemetria'
   SIN cláusula WHERE, y dos acciones: escribir en la tabla (usa la acción
   DynamoDBv2) y escribir en el bucket.

4. El rol de IAM que la regla necesita, con permisos solo sobre esa tabla y
   ese bucket.

Antes de crear la regla, dime por qué esta no lleva WHERE y la anterior sí.
```

**Qué revisar tú:** que la tabla quede en modo **aprovisionado** y que la
regla **no** tenga `WHERE`. Y pídele la respuesta a esa última pregunta: si
no sabe explicarlo, probablemente tampoco entendió lo que estaba haciendo.

## Paso 5 · Comprobar que funciona de verdad

```
Dame una lista de comandos de SOLO LECTURA para verificar yo mismo que todo
quedó bien montado:

- qué Things, certificados y políticas existen, y qué está adjunto a qué
- qué reglas hay, su SQL, si están activas y qué acciones tienen
- con qué rol corre la Lambda y qué permisos tiene ese rol
- si el tema de SNS tiene mi suscripción confirmada
- las últimas líneas de los registros de la función

Solo los comandos. Los ejecuto yo.
```

Esto es lo más valioso de toda la guía: **te quedas con la forma de
comprobar, no solo con el resultado.**

## Paso 6 · Borrarlo todo

```
Dame los comandos para borrar TODO lo que creamos en esta conversación, en el
orden correcto de dependencias, y explícame por qué ese orden.

No los ejecutes: quiero revisarlos uno por uno antes.

Avísame si queda algo que no se pueda borrar o que vaya a seguir generando
costo.
```

> El orden importa y es una buena pregunta de examen: no puedes borrar un
> certificado que sigue adjunto a un Thing, ni una política que sigue adjunta
> a un certificado. Hay que desengancharlo todo primero.

---

## Cómo saber si el agente se equivocó

No te fíes del «listo, ya está». Estas cuatro comprobaciones las haces tú, y
cubren los errores que de verdad ocurren:

| Comprueba | Comando |
|---|---|
| Quién eres y dónde estás | `aws sts get-caller-identity` |
| Qué reglas hay y cómo son | `aws iot list-topic-rules` |
| Si una política quedó activa | `aws iot get-policy --policy-name lab-politica` |
| Qué se está gastando | Consola → **Facturación** → **Presupuestos** |

Y la de siempre, la que funciona de verdad: **arranca tu dispositivo y mira
si pasa lo que esperabas.**

---

## Lo que no le pidas

- **Que te configure las credenciales.** Eso lo haces tú, una vez, con
  `aws configure`.
- **Que borre cosas «que no hagan falta».** Tu cuenta tiene recursos de otras
  clases. Que borre solo lo que creó él, y con tu permiso.
- **Que suba nada a un repositorio.** Tus certificados y tu `.env` no se
  publican, y un agente con prisa no distingue.
- **Que haga el laboratorio por ti la primera vez.** Vuelve al principio de
  esta página.
