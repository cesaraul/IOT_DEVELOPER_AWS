# Constructor de plantillas

Una plantilla de CloudFormation leída de corrido parece magia: se entiende
qué hace cada campo, pero no de dónde salen ni por qué esos y no otros.

Esta herramienta la construye **delante de ti**. Eliges a la izquierda, el
YAML se escribe a la derecha, y al final se guarda en tu disco con el
comando listo para ejecutar.

```bash
docker compose up
```

Y abre <http://localhost:8081>.

> Va en el **8081** porque el simulador de reglas de la clase 5 usa el 8080:
> puedes tener los dos abiertos.

---

## Lo que hace, y lo que no

**No toca AWS.** No sabe nada de tus credenciales, no las pide y no las
necesita. Construye un archivo de texto y lo escribe en la carpeta del
laboratorio. **Desplegarlo es cosa tuya**, desde tu terminal, con tu perfil.

Esa separación es a propósito: una herramienta de clase con tus claves
dentro sería mala idea, y además se saltaría el paso que importa.

---

## El recorrido

| | |
|---|---|
| **Lo que ya existe** | Plegado arriba. El objeto, la política, la Lambda y el tema de SNS de las clases anteriores. Está para que veas el conjunto, pero **no entra en la plantilla**: ya existe |
| **1 · Tu dispositivo** | El nombre. Se usa como prefijo de todo |
| **2 · La tabla** | Las dos claves y el modo de capacidad |
| **3 · Dónde guardar** | DynamoDB, S3, o los dos |
| **4 · La regla** | Qué campos añade la consulta, y si filtra |
| **5 · ¿Ya desplegaste?** | No cambia el YAML: activa un aviso |

Cada bloque trae el **enlace a la documentación** del recurso que genera.
Ahí está la respuesta a *«¿cómo sabe alguien que esos son los campos?»*:
cada `AWS::Servicio::Recurso` tiene su página con todas sus propiedades y
cuáles son obligatorias. Nadie se las sabe de memoria — **se consultan.**

---

## Lo que de verdad enseña: los avisos

Leer un YAML que funciona no deja ver lo que más cuesta entender: **que los
recursos se necesitan entre sí.** Aquí sí se ve, porque al cambiar algo el
aviso aparece al instante.

| Si haces esto | Lo que te dice |
|---|---|
| Quitas `parse_time(...) AS momento` | La tabla usa `momento` como clave y ya nadie lo genera: DynamoDB rechazará cada fila |
| Pones la clave de ordenación como número | `parse_time` devuelve texto: el tipo no cuadra |
| Pones la tabla bajo demanda | Sale del Free Tier permanente |
| Le pones `WHERE` a la regla de guardar | Estás filtrando lo que guardas |
| Cambias el nombre de una clave | `consultar.py` busca la otra: dejará de encontrar tus filas |
| Desmarcas S3 | El permiso `s3:PutObject` **desaparece del rol**, delante de ti |

**Ninguno bloquea nada.** Puedes guardar y desplegar una plantilla rota: es
tu cuenta, son datos de prueba, y equivocarse es la parte barata de
aprender.

---

## Guardar y desplegar

El botón **Guardar plantilla** escribe el archivo en:

```
labs/06-almacenamiento/mi-clase6.yaml
```

y te enseña el comando con esa ruta. No hay que copiar el YAML a ningún
sitio.

Tu nombre queda como **valor por defecto del parámetro**, así que el comando
no necesita pasárselo. Pero sigue siendo un parámetro: esa misma plantilla
sirve para otro equipo con `--parameter-overrides NombreObjeto=otro`.

> Si cambias algo después de guardar, el mensaje desaparece: lo guardado ya
> no es lo que ves. Vuelve a darle.

---

## Una advertencia sobre reemplazos

Si ya desplegaste la pila y luego **cambias una clave de la tabla**,
CloudFormation no la modifica: **la borra y crea otra**, con los datos
dentro.

Lo verás en la columna `Reemplazo` del conjunto de cambios, y es justo el
motivo por el que esa columna existe:

```bash
aws cloudformation deploy ... --no-execute-changeset
```

En el curso no importa —son datos de prueba— y por eso es el mejor momento
para que te pase.

---

## Si quieres mirar por dentro

| Archivo | Qué hace |
|---|---|
| `servidor.py` | Cuarenta líneas, sin dependencias. Sirve la página y escribe el archivo |
| `web/js/plantilla.js` | Genera el YAML. Cada decisión escribe unas líneas concretas |
| `web/js/avisos.js` | Las comprobaciones cruzadas |
| `web/js/app.js` | El pegamento |

---

## Para parar

```bash
docker compose down
```
