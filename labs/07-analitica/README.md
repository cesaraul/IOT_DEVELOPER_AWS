# Clase 7 · Preguntar y ver

Hasta ahora los datos **entraban**. Hay una tabla con el estado y un bucket
con el histórico, y nadie los ha mirado todavía: para verlos hemos tenido
que usar la consola de AWS o un script en la terminal.

Hoy se le da la vuelta. Vas a construir **lo que va delante de los datos**:
una pieza que recibe una pregunta por HTTPS, busca, y contesta. Y una
página que la usa.

```
   Tu navegador              Tu Lambda                  Lo de la clase 6
  ┌──────────────┐  HTTPS   ┌────────────┐   permiso   ┌──────────────┐
  │ el panel     │ ───────► │ la API     │ ──────────► │  DynamoDB    │
  │ (localhost)  │ ◄─────── │ (consulta) │ ◄────────── │  S3          │
  └──────────────┘   JSON   └────────────┘             └──────────────┘
```

Fíjate en quién tiene permisos: **la Lambda**. El navegador no tiene
credenciales de AWS y no las necesita. Así funciona cualquier aplicación
que hayas usado nunca.

---

## Lo que vas a usar

| Recurso | Qué es | Por qué aquí |
|---|---|---|
| `AWS::Lambda::Function` | Código que corre cuando alguien lo llama | Es quien sabe buscar y tiene el permiso para hacerlo |
| `AWS::Lambda::Url` | Una dirección HTTPS para esa función | Sin ella harían falta API Gateway y una clase entera más |
| `AWS::Lambda::Permission` | Quién puede invocarla | El cuarto tipo de identidad del curso: no *quién eres*, sino *a quién dejas entrar* |
| `AWS::IAM::Role` | La identidad de la función | Solo lectura. La regla que escribe tiene su propio rol |
| `AWS::IoT::TopicRule` | Otra regla, con acción de CloudWatch | Para la última parte: la métrica que no hubo que programar |

Todo sigue en capa gratuita: la Lambda tiene 1 M de invocaciones al mes
siempre gratis, y la métrica entra en las 10 personalizadas del Free Tier
permanente de CloudWatch.

---

## Paso 0 · Mira en qué cuenta estás

```powershell
aws sts get-caller-identity --profile curso
```

Tiene que salir la cuenta del curso. Si sale otra, para: desplegarías la
pila donde no hay datos y pasarás media clase buscando por qué la API
contesta con una lista vacía.

Y comprueba que lo de la clase 6 sigue en pie, porque hoy se lee de ahí:

```powershell
aws cloudformation describe-stacks --stack-name clase6 --query "Stacks[0].StackStatus" --profile curso
```

---

## Paso 1 · Lee la plantilla antes de desplegarla

Está en [`infra/clase7.yaml`](../../infra/clase7.yaml). Son seis recursos y
ya conoces la forma de todos. Dos cosas en las que merece la pena pararse:

**El rol solo sabe leer.** `dynamodb:Query`, `s3:GetObject`,
`s3:ListBucket`. Nada de escribir. No es paranoia: es que una función que
solo consulta no tiene por qué poder borrar tu histórico, y así, si
mañana tiene un fallo, lo peor que puede pasar es que enseñe datos que
ya son tuyos.

**La dirección es pública.** `AuthType: NONE` significa que cualquiera
con esa URL puede preguntar. Para una clase vale; en producción, jamás.
Por eso el último paso de este laboratorio es borrar la pila.

---

## Paso 2 · Despliega

```powershell
aws cloudformation deploy --template-file infra/clase7.yaml --stack-name clase7 --capabilities CAPABILITY_NAMED_IAM --region us-east-2 --profile curso --parameter-overrides NombreObjeto=tu-dispositivo
```

Pon en `NombreObjeto` **el mismo nombre de la clase 6**. De ahí salen el
nombre de la tabla y del bucket que la función va a leer.

Al terminar, pide la dirección:

```powershell
aws cloudformation describe-stacks --stack-name clase7 --query "Stacks[0].Outputs" --profile curso
```

---

## Paso 3 · Pregúntale desde la terminal

Antes del panel, una vez a pelo. Es importante ver que la API es solo una
dirección, y que no hay nada mágico en el panel:

```powershell
curl.exe "https://TU-DIRECCION.lambda-url.us-east-2.on.aws/?accion=ultimas&dispositivo=tu-dispositivo&n=3"
```

Debe volver un JSON con tus filas. Si vuelve `{"filas": []}` es que la
tabla está vacía o el `dispositivo` no coincide: arranca el equipo de la
clase 4 un minuto y vuelve a preguntar.

---

## Paso 4 · El panel

```powershell
cd labs/07-analitica/panel
docker compose up
```

Y abre <http://localhost:8082>. Pega arriba la dirección de tu API.

El panel sabe hacer cuatro preguntas, y no son cuatro al azar:

| Pregunta | Quién contesta | Lo que enseña |
|---|---|---|
| ¿Cómo está ahora? | DynamoDB | La consulta por clave de partición |
| ¿Qué pasó entre estas dos horas? | DynamoDB | Para esto existe la clave de **ordenación** |
| ¿Cuántas veces pasó del umbral? | DynamoDB | La Lambda **calcula**: devuelve una conclusión, no datos |
| ¿Y el día completo? | S3 | El almacén barato, y lo que cuesta leerlo |

Mira el recuadro **«Quién contestó»** cada vez. Trae los milisegundos.
Compara la primera pregunta con la última: la diferencia entre *caliente*
y *frío* de la clase pasada deja de ser una metáfora y se convierte en un
número.

> La parte que de verdad hay que mirar es **la dirección que se va a
> pedir**, a la derecha. Cada campo que tocas a la izquierda aparece ahí
> como un parámetro. Eso es todo lo que esta página le dice a AWS.

---

## Paso 5 · La métrica que no programaste

La misma pila ha creado una segunda regla con una acción que no habíamos
usado: `CloudwatchMetric`. Coge el `nivel` de cada mensaje y lo deja como
una métrica.

1. Arranca el equipo de la clase 4 y déjalo publicar un par de minutos.
2. Consola → **CloudWatch** → **Métricas** → **Todas las métricas**.
3. Busca el espacio de nombres **`FabLab/Tanques`**.
4. Marca la de tu dispositivo y pon el periodo en 1 minuto.

Y ahí está la curva. **Sin escribir una línea de código.**

Ese es el contraste de la clase: el panel lo has construido tú y hace
exactamente lo que quieres; la métrica venía hecha y no se puede cambiar.
Las dos cosas son decisiones legítimas, y saber cuándo tomar cada una es
de lo que va este oficio.

---

## Errores comunes

| Lo que ves | Lo que pasa |
|---|---|
| `403 Forbidden` al llamar la URL | Faltan permisos de invocación. La plantilla trae los **dos** que hacen falta desde octubre de 2025; si copiaste un ejemplo de internet, seguramente solo trae uno |
| `{"filas": []}` | La tabla no tiene nada de ese `dispositivo`, o el nombre no coincide exactamente |
| `AccessDeniedException` en la respuesta | El rol de la Lambda no tiene ese permiso. Se arregla en la plantilla y se vuelve a desplegar, no en la consola |
| El `curl` funciona y el panel no | Es CORS: el navegador exige que la respuesta lo autorice. Lo pone la función en sus cabeceras, y la URL en su configuración |
| La ventana de tiempo no devuelve nada | El `momento` está en **UTC**. El panel convierte tu hora local; si preguntas con `curl` a mano, conviértela tú |
| Tarda 3 segundos la primera vez | Es el arranque en frío. La segunda vuela: el contenedor sigue vivo. Lo mismo de la clase 5 |

---

## Al terminar · borra la pila

**Esto no es opcional.** Mientras la pila exista hay una dirección HTTPS
pública que entrega tus datos a cualquiera que la tenga.

```powershell
aws cloudformation delete-stack --stack-name clase7 --region us-east-2 --profile curso
```

Y para parar el panel:

```powershell
docker compose down
```

La pila de la clase 6 —la tabla, el bucket y la regla que guarda— puede
quedarse: ahí no hay nada abierto al mundo. Si tampoco la quieres,
`delete-stack --stack-name clase6`. Ojo: se va la tabla con los datos
dentro.
