# El laboratorio en un archivo

`laboratorio.yaml` es una **plantilla de CloudFormation**: describe en texto
todo lo que construiste a clics en las clases 3 a 6. Con un comando lo creas
entero, y con otro lo borras entero.

| Crea | De qué clase |
|---|---|
| El objeto y su política (con los permisos del shadow) | 3 y 4 |
| El tema de SNS y tu suscripción de correo | 5 |
| La función Lambda, su rol y el permiso de invocación | 5 |
| La regla de alarmas, con su rol | 5 |
| La tabla de DynamoDB y el bucket de S3 | 6 |
| La regla de guardar, con su rol | 6 |

---

## Paso 0 · Mira en qué cuenta estás

**Hazlo siempre, aunque creas que lo sabes.**

```bash
aws sts get-caller-identity
```

Si tienes más de una cuenta de AWS —la del curso y otra—, el CLI apunta a
**una sola**, y no necesariamente a la que crees. Desplegar en la cuenta
equivocada no da ningún error: simplemente crea todo donde no querías.

> Esto nos pasó montando esta misma plantilla: el CLI apuntaba a otra cuenta
> y la prueba se desplegó ahí. Se arregla con un perfil aparte:
>
> ```bash
> aws configure --profile curso
> ```
>
> y añadiendo `--profile curso` a todos los comandos.

## Paso 1 · Desplegarlo

```bash
aws cloudformation deploy --template-file infra/laboratorio.yaml --stack-name lab-iot --capabilities CAPABILITY_NAMED_IAM --region us-east-2 --parameter-overrides NombreObjeto=cesar-01 Correo=tu@correo.com
```

Tres cosas de ese comando:

- **`NombreObjeto`** en minúsculas y sin espacios. Se usa como nombre del
  dispositivo y como prefijo de la tabla y del bucket.
- **`CAPABILITY_NAMED_IAM`** es obligatorio porque la plantilla crea roles
  con nombre propio. Es AWS pidiéndote que confirmes que sabes que va a
  tocar permisos.
- **`--region`** la tuya. Si te equivocas aquí, nada de lo que creaste en
  las clases anteriores aparecerá.

Tarda un par de minutos. Cuando termine, **confirma el correo** que te llegó
de AWS: hasta entonces no recibirás ninguna alarma.

## Paso 2 · El certificado, que la plantilla no puede crear

> **Y esto no es una limitación de CloudFormation: es la misma regla de
> seguridad de la clase 3.**
>
> La llave privada se entrega **una sola vez**, en el momento de crear el
> certificado, y AWS no la guarda. Si una plantilla pudiera generarla,
> tendría que guardarla en algún sitio — y entonces dejaría de ser secreta.

```bash
aws iot create-keys-and-certificate --set-as-active --certificate-pem-outfile certificados/dispositivo.cert.pem --private-key-outfile certificados/dispositivo.private.key --query certificateArn --output text
```

Guarda el ARN que te devuelve y engánchalo a lo que creó la plantilla:

```bash
aws iot attach-policy --policy-name cesar-01-politica --target "EL-ARN-DEL-CERTIFICADO"
```

```bash
aws iot attach-thing-principal --thing-name cesar-01 --principal "EL-ARN-DEL-CERTIFICADO"
```

Y el certificado raíz de Amazon, que es público:

```bash
curl -o certificados/AmazonRootCA1.pem https://www.amazontrust.com/repository/AmazonRootCA1.pem
```

## Paso 3 · Tu endpoint

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS
```

Ese valor va en el `.env` de los laboratorios, junto con el nombre del
objeto. Ya puedes arrancar el dispositivo de siempre.

## Paso 4 · Borrarlo todo

```bash
aws cloudformation delete-stack --stack-name lab-iot --region us-east-2
```

**Esto es lo que más vale de toda la plantilla.** Borra las dos reglas, la
función, los tres roles, el tema, la tabla y el bucket — en el orden correcto
de dependencias, sin que se te olvide nada.

Es la solución al problema que arrastramos desde la clase 3: recursos
olvidados gastando en veinte cuentas distintas.

> **Dos cosas que tendrás que borrar a mano:**
> - **El certificado**, porque no lo creó la plantilla. Hay que desadjuntarlo
>   primero (`detach-policy`, `detach-thing-principal`) y después
>   `update-certificate --new-status INACTIVE` y `delete-certificate`.
> - **El bucket, si tiene objetos dentro.** CloudFormation no borra buckets
>   con contenido: primero `aws s3 rm s3://TU-BUCKET --recursive`.

---

## Qué mirar en la plantilla

Está comentada para leerse, no solo para ejecutarse. Tres cosas que vale la
pena buscar dentro:

**La política del dispositivo** usa `${iot:Connection.Thing.ThingName}`, no
el nombre escrito a mano. Por eso una sola política sirve para toda la clase.

**Las dos reglas no son iguales**: la de alarmas lleva `WHERE` y la de
guardar no. Se filtra lo que se avisa, no lo que se guarda.

**`PermisoDeInvocacion`** es el permiso para que la regla pueda llamar a la
función, y vive **en la función**, no en la regla. Si falta, la regla se ve
perfecta y la función no se ejecuta nunca, sin un solo error en ninguna
parte. Es el fallo más difícil de diagnosticar del curso, y aquí son seis
líneas que no se pueden olvidar.

---

## Probada de verdad

Esta plantilla se desplegó en una cuenta real antes de publicarla: los trece
recursos se crearon correctamente y la pila se borró sin dejar restos.
