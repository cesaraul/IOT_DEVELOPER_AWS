# Laboratorio 06 — Almacenamiento

En la clase 5 los datos **pasaban**: la regla los evaluaba, la función los
imprimía, y se perdían. Si mañana alguien pregunta *«¿a qué hora se desbordó
el tanque el martes?»*, no hay dónde mirar.

Hoy quedan guardados. Y hoy, además, **no vamos a hacer un solo clic en la
consola.**

---

## Por qué hoy no hacemos clics

Llevas cuatro clases creando cosas a mano, y ya sabes lo que cuesta: la
política que se guardó sin activar, el permiso que se perdió al recrear la
función, los certificados huérfanos que quedaron por el camino.

Ahora imagina repetir todo eso **veinte veces**, una por cada equipo de una
planta. O rehacerlo en otra región. O explicarle a alguien exactamente qué
creaste hace tres meses.

> **Una plantilla de CloudFormation es tu arquitectura escrita en un
> archivo.** Se lee, se versiona, se revisa como código — y se despliega
> igual la primera vez que la número cien.

No es que los clics estén mal. Es que **no se pueden repetir, ni revisar, ni
deshacer**. Y eso último es lo que más vas a agradecer hoy.

---

## Antes de empezar

| Necesitas | Dónde |
|---|---|
| El AWS CLI instalado y configurado | [guía](../../docs/acceso-desde-tu-laptop.md) |
| Tu usuario de IAM y sus claves | la misma guía |
| El dispositivo de la clase 4, funcionando | `labs/04-device-shadow` |

**Comprueba en qué cuenta estás antes de nada:**

```bash
aws sts get-caller-identity
```

Si tienes más de una cuenta de AWS, el CLI apunta a **una sola** y no
necesariamente a la que crees. Desplegar en la cuenta equivocada no da
ningún error: crea todo donde no querías.

---

## Paso 1 · Leer la plantilla antes de ejecutarla

Abre [`infra/clase6.yaml`](../../infra/clase6.yaml). **Léela entera antes de
desplegar nada.** Son cuatro recursos y cabe en una pantalla.

Tiene tres secciones, y son siempre las mismas en cualquier plantilla:

| Sección | Qué es |
|---|---|
| `Parameters` | Lo que cambia de una persona a otra. Por eso los veinte de la clase despliegan **el mismo archivo** |
| `Resources` | Lo que se crea. Un bloque por recurso |
| `Outputs` | Lo que te devuelve al terminar, para que no tengas que ir a buscarlo |

Y cada recurso tiene siempre esta forma:

```yaml
NombreQueLeDasTu:
  Type: AWS::Servicio::Recurso
  Properties:
    ...lo que ese recurso necesita...
```

### Las cuatro preguntas que deberías saber responder

Antes de desplegar, busca en el archivo:

1. **En el bloque `Tabla`, ¿dónde están `nivel` y `temp`?**
   No están. Solo se declaran las columnas que forman la clave; las demás
   aparecen solas con lo que traiga cada mensaje.

2. **¿Por qué la tabla es `PROVISIONED` y no bajo demanda?**
   Porque el Free Tier permanente de DynamoDB solo cubre ese modo.

3. **¿Por qué la regla de hoy no tiene `WHERE`, y la de la clase 5 sí?**
   Se filtra lo que se avisa, no lo que se guarda.

4. **¿Qué hace `!GetAtt Tabla.Arn` dentro del rol?**
   Coge un dato de otro recurso de la misma plantilla. Así el permiso
   apunta exactamente a tu tabla y a ninguna otra, sin que tengas que
   escribir su ARN a mano.

> Si alguna de las cuatro no te sale, **para aquí**. El objetivo de hoy no
> es desplegar: es que esto deje de parecer magia.

## Paso 2 · Desplegar

```bash
aws cloudformation deploy --template-file infra/clase6.yaml --stack-name clase6 --capabilities CAPABILITY_NAMED_IAM --region us-east-2 --parameter-overrides NombreObjeto=tu-dispositivo
```

Cambia `tu-dispositivo` por el nombre del tuyo, en minúsculas.

Tres cosas de ese comando:

- **`--stack-name clase6`** — la *pila* es el conjunto. Todo lo que creamos
  queda agrupado bajo ese nombre, y por eso se puede borrar junto.
- **`--capabilities CAPABILITY_NAMED_IAM`** — obligatorio porque la plantilla
  crea un rol con nombre propio. Es AWS pidiéndote que confirmes que sabes
  que va a tocar permisos.
- **`--region`** — la tuya.

Tarda un par de minutos. Verás:

```
Waiting for changeset to be created..
Waiting for stack create/update to complete
Successfully created/updated stack - clase6
```

### Qué acaba de pasar

CloudFormation no ejecutó los cuatro bloques en orden de arriba abajo:
**calculó las dependencias**. El rol necesita el ARN de la tabla, así que la
tabla va primero. La regla necesita el rol, así que va después. Tú escribiste
*qué* querías; el orden lo resolvió él.

## Paso 3 · Mirar lo que creó

```bash
aws cloudformation describe-stack-resources --stack-name clase6 --query "StackResources[].{Recurso:LogicalResourceId,Estado:ResourceStatus}" --output table
```

Cuatro recursos en `CREATE_COMPLETE`. Y los nombres que necesitas:

```bash
aws cloudformation describe-stacks --stack-name clase6 --query "Stacks[0].Outputs" --output table
```

## Paso 4 · Configurar el laboratorio

```bash
cd labs/06-almacenamiento
```

```bash
cp .env.example .env
```

Rellena el `.env` con tus claves, tu `DISPOSITIVO_ID`, y la `TABLA` y el
`BUCKET` que te acaban de dar los Outputs.

Y comprueba:

```bash
docker compose run --rm app python comprobar.py
```

Revisa cinco cosas en orden —tus claves, la tabla, el bucket, la regla y si
está entrando algo— y te dice exactamente qué falta en cada caso.

## Paso 5 · Encender el dispositivo

En otra terminal, el de siempre. **No se le toca nada**: publica igual que
ayer, y no sabe que ahora alguien está guardando lo que dice.

```bash
cd ../04-device-shadow
```

```bash
docker compose run --rm dispositivo python shadow_dispositivo.py
```

Déjalo un par de minutos.

## Paso 6 · Ver los datos — el momento de la clase

Vuelve al laboratorio 06:

```bash
docker compose run --rm app python consultar.py
```

```
  10 fila(s) de 'tu-dispositivo'

  momento                      nivel    temp   alarma
  -------------------------- ------- -------   ------
  2026-11-23T10:05:31.002Z      82.4    24.1   SI
  2026-11-23T10:05:21.114Z      78.9    23.8
  ...
```

**Ahí están tus lecturas.** Salieron de tu laptop, pasaron por una regla que
escribiste en un archivo de texto, y quedaron guardadas sin que ningún
programa tuyo estuviera escuchando.

### Y ahora la clave de ordenación, en acción

```bash
docker compose run --rm app python consultar.py --rango 10:00 10:30
```

Eso **no recorre la tabla**: va directo, porque dentro de cada dispositivo
las filas están ordenadas por `momento`. Es exactamente para lo que elegimos
esa clave.

### El otro lado

```bash
docker compose run --rm app python explorar.py
```

```
  47 archivo(s) en tu-dispositivo-telemetria-123456789012
  Equipos: tu-dispositivo

  Los más recientes:
      68 B   tu-dispositivo/2026/11/23/8f2c....json
```

Y abre uno:

```bash
docker compose run --rm app python explorar.py --abrir tu-dispositivo/2026/11/23/8f2c....json
```

> **Compara los dos comandos y tienes la clase entera.**
>
> A DynamoDB le pediste *«las últimas diez de este equipo»* y fue directo.
> A S3 no le puedes pedir eso: solo sabe listar nombres y entregar archivos.
> Si quisieras *«los mensajes donde el nivel pasó de 90»*, tendrías que
> bajarte todos y mirarlos uno a uno.
>
> No es un defecto: **es lo que lo hace diez veces más barato.** Y para
> preguntarle cosas a S3 existe Athena, que es la clase 7.

## Paso 7 · Cambiar algo y volver a desplegar

Esto es lo que no se puede hacer con clics. Abre la plantilla y cambia la
capacidad de la tabla de `1` a `2`. Y antes de aplicar nada:

```bash
aws cloudformation deploy --template-file infra/clase6.yaml --stack-name clase6 --capabilities CAPABILITY_NAMED_IAM --region us-east-2 --parameter-overrides NombreObjeto=tu-dispositivo --no-execute-changeset
```

Con `--no-execute-changeset` **no cambia nada**: te dice qué cambiaría y se
para. Eso es un *conjunto de cambios*, y no existe en la consola a clics.

```
Changeset created successfully. Run the following command to review changes:
aws cloudformation describe-change-set --change-set-name arn:aws:cloudformation:...
```

Copia ese comando y añádele `--output table` para leerlo:

```
+--------+-------------------------+---------------+-------------+
| Accion |        Propiedad        |    Recurso    |  Reemplazo  |
+--------+-------------------------+---------------+-------------+
|  Modify|  ProvisionedThroughput  |  Tabla        |  False      |
|  Modify|  TopicRulePayload       |  ReglaGuardar |  False      |
|  Modify|  Policies               |  RolRegla     |  False      |
+--------+-------------------------+---------------+-------------+
```

**Mira la columna `Reemplazo`.** Es la más importante de las cuatro: `False`
significa que AWS va a **modificar** el recurso que existe. Si pusiera
`True`, lo borraría y crearía otro — y con una tabla, eso sería perderlo
todo. Esa columna es la que revisas antes de aplicar un cambio en
producción.

> Verás tres recursos aunque solo tocaras uno. CloudFormation marca como
> «modificados» los que vuelve a evaluar, aunque el resultado sea idéntico.
> Lo que importa es que ninguno se reemplaza.

> *«Mira qué va a cambiar antes de cambiarlo.»* El día que trabajes en una
> infraestructura de verdad, eso es la diferencia entre una revisión y un
> susto.

Quita el `--no-execute-changeset` y vuelve a lanzarlo: **modifica la tabla
existente**, no crea otra. CloudFormation compara lo que hay con lo que pides
y aplica solo la diferencia.

## Paso 8 · Borrarlo todo

```bash
aws cloudformation delete-stack --stack-name clase6 --region us-east-2
```

**Un comando, y desaparecen los cuatro recursos** — en el orden correcto de
dependencias, sin que se te olvide nada.

Acuérdate de lo que costó al final de las clases 3, 4 y 5: ir recurso por
recurso, desadjuntar certificados, desactivar reglas, y aun así dejarse
cosas. Esa es la razón de ser de todo esto.

> **Si falla**, casi siempre es el bucket: S3 no deja borrar un bucket con
> archivos dentro. Vacíalo primero:
>
> ```bash
> aws s3 rm s3://TU-BUCKET --recursive
> ```

---

## Errores comunes

| Lo que ves | Qué pasa |
|---|---|
| `Parameter NombreObjeto failed to satisfy constraint` | Lleva mayúsculas o espacios. Solo minúsculas, números y guiones |
| `requires capabilities: [CAPABILITY_NAMED_IAM]` | Falta ese parámetro en el comando |
| `BucketAlreadyExists` | El nombre de bucket es único en todo el mundo. La plantilla le pega tu número de cuenta, así que esto solo pasa si lo cambiaste |
| El comprobador dice que no encuentra la tabla | Estás en otra región, o `TABLA` en el `.env` no coincide con el Output |
| Hay filas en la tabla pero el bucket está vacío | Mira el rol: a lo mejor tiene el permiso de DynamoDB y no el de S3 |
| No entra nada en ninguno de los dos | El dispositivo no está encendido, o publica en otro topic |
| `delete-stack` se queda en `DELETE_FAILED` | El bucket tiene archivos. Vacíalo y repite |

---

## Lo que cuesta

| Servicio | Gratis | Ojo |
|---|---|---|
| DynamoDB | 25 GB y 25 unidades de cada tipo, **permanente** | Solo en modo aprovisionado |
| S3 | 5 GB y **2.000 PUT al mes**, 12 meses | Cada mensaje guardado es un PUT: a uno cada 10 segundos son 8.640 al día |

Lo segundo son céntimos aquí, pero **es también un error de diseño**: un
archivo por mensaje no se hace en producción. Se acumulan en lotes y se
escribe uno cada pocos minutos. Eso lo hace Kinesis Firehose, y es lo que
viene en la clase 7.

Por eso el paso 8 no es opcional.
