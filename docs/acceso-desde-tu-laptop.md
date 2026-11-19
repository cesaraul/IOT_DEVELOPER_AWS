# Conectar tu laptop a AWS

Hasta ahora, lo único que entraba a tu cuenta desde tu computadora era **tu
dispositivo**, con su certificado. Pero los programas que escribes tú —el que
consulta el shadow, el que lee la tabla, el que mira los registros— no son
dispositivos: son **aplicaciones**, y entran de otra forma.

Esta guía crea esa segunda identidad. Se hace **una vez** y sirve para todo lo
que queda del curso.

---

## Por qué no usar la cuenta con la que entras

La cuenta con la que te registraste —la **raíz**— lo puede todo: borrar la
cuenta, cambiar la tarjeta, cerrar servicios. Está atada a tu medio de pago.
No se usa para trabajar, y mucho menos para que la use un programa.

| Quién | Se identifica con | Dónde lo viste |
|---|---|---|
| Un dispositivo | certificado X.509 | clase 3 |
| **Una aplicación o tú** | **usuario de IAM + claves** | **aquí** |
| Un servicio de AWS | rol de IAM | clase 5 |

> **La idea que hay que llevarse:** un usuario de IAM es a un programa lo que
> el certificado X.509 es a tu dispositivo. **Identidades de máquina, no de
> persona.** Verás que AWS ni siquiera te deja darle contraseña de consola.

---

## Paso 1 · Crear el usuario

1. Buscador de la consola → **IAM** → entra.
2. Menú izquierdo → **Usuarios** → **Crear usuario**.
3. Nombre: algo que identifique para qué es, por ejemplo `cesar-curso`.
4. **No marques** la casilla de acceso a la consola de administración.

> Si la marcas, AWS te avisa de que los usuarios de IAM son para **acceso
> programático** y que a las personas se las invita desde la página del
> equipo. Hazle caso: este usuario es para tus programas.

5. **Siguiente**.

## Paso 2 · Darle permisos

En **Establecer permisos** → **Adjuntar políticas directamente**, busca y
marca estas tres:

| Política | Para qué |
|---|---|
| `AWSIoTDataAccess` | Hablar con tus dispositivos y sus shadows |
| `AmazonDynamoDBReadOnlyAccess` | Leer la tabla de telemetría (clase 6) |
| `AmazonS3ReadOnlyAccess` | Leer el histórico (clase 6) |

**Siguiente** → revisa → **Crear usuario**.

> **Fíjate en la pantalla de revisión:** dice *«Tipo de contraseña de consola:
> None»*. Este usuario **no puede entrar a la consola**, ni aunque quisieras.
> Solo tendrá claves, para que las use un programa.

> **Por qué solo lectura en DynamoDB y S3:** tus programas van a *consultar*
> lo que la regla guardó. Quien escribe ahí es AWS, con su propio rol. Si tu
> programa no necesita escribir, no le des permiso para escribir — el día que
> tenga un fallo, el daño posible es mucho menor.

## Paso 3 · Crear la clave de acceso

1. **IAM** → **Usuarios** → tu usuario → pestaña **Credenciales de
   seguridad**.
2. Baja hasta **Claves de acceso** → **Crear clave de acceso**.
3. Caso de uso: **«Aplicación que se ejecuta fuera de AWS»** → **Siguiente**.
4. Etiqueta (opcional): `laboratorio` → **Crear clave de acceso**.
5. **No cierres esa pantalla todavía.**

> ### La clave secreta se muestra UNA sola vez
>
> Exactamente igual que la llave privada de tu certificado. Si cierras la
> ventana sin copiarla, **no se recupera**: hay que borrar esa clave y crear
> otra. Son treinta segundos, pero mejor no pasar por ahí.
>
> Reconoce el patrón, porque se repite en toda la nube: **AWS nunca te vuelve
> a enseñar un secreto.**

Vas a tener dos cadenas:

- **Id de clave de acceso**: empieza por `AKIA…`. Es el «usuario».
- **Clave de acceso secreta**: una cadena larga. Es la «contraseña».

## Paso 4 · Ponerlas en tu laptop

Los laboratorios las leen de un archivo `.env`. Desde la carpeta del
laboratorio:

```bash
cp .env.example .env
```

```powershell
Copy-Item .env.example .env
```

Abre ese `.env` y pega las dos cadenas:

```ini
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

Ahora sí, cierra la pantalla de AWS.

> **El archivo se llama `.env`, no `.env.example`.** El del `.example` es la
> plantilla que viene en el repositorio y **sí se publica**: si pegas tus
> claves ahí, acaban en GitHub. Es el error más fácil de cometer de toda
> esta guía.

### Tres reglas sobre esas claves

1. **Valen tanto como la contraseña de tu cuenta.** Con ellas se entra a AWS.
2. **No se comparten.** Ni por WhatsApp, ni por correo, ni con el instructor.
   Nadie necesita las tuyas.
3. **No se suben a ningún repositorio.** El `.gitignore` del curso ya excluye
   los `.env`, pero esa red no te salva si las pegas en otro archivo.

> Si alguna vez se te escapa una —pasa más de lo que parece—, entra a
> **IAM → tu usuario → Credenciales de seguridad** y **bórrala**. Crear otra
> toma treinta segundos; que alguien mine criptomonedas en tu cuenta, no.

## Paso 5 · Comprobar que funciona

Desde la carpeta del laboratorio 04:

```bash
docker compose run --rm dispositivo python comprobar.py
```

Los pasos **6 y 7** del comprobador son justamente esto: que las claves estén
puestas y que AWS las acepte. Si salen en verde, ya tienes las dos
identidades funcionando — el dispositivo con su certificado y tu aplicación
con sus claves.

---

## Si algo falla

| Lo que ves | Qué pasa |
|---|---|
| `faltan AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY` | El archivo se llama `.env.example` en vez de `.env`, o está en otra carpeta |
| `UnrecognizedClientException` / `InvalidSignatureException` | La clave está incompleta al copiar, o la borraste en IAM |
| `AccessDeniedException` | Falta una de las tres políticas del paso 2 |
| `boto3 no encontró tus claves` | Quedó un espacio o unas comillas en el `.env`. Va `CLAVE=valor`, sin comillas |

---

## Al terminar el curso

Entra a **IAM → Usuarios → tu usuario → Credenciales de seguridad** y
**elimina la clave de acceso**. No la desactives: bórrala.

Una credencial que ya no usas y sigue viva es exactamente el tipo de cosa que
alguien encuentra dos años después en un repositorio viejo.

> **Y una nota para cuando trabajes en serio:** las claves de larga duración
> como estas son cómodas para aprender, pero en producción se evitan. Lo que
> se usa hoy son credenciales temporales que caducan solas (IAM Identity
> Center, roles). Si en una entrevista te preguntan por esto, esa es la
> respuesta.
