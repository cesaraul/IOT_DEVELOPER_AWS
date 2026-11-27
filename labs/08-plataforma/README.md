# Clase 8 · Tu sistema, entero

Ocho clases construyendo piezas sueltas. Esta herramienta las junta en una
pantalla para que veas **el conjunto**, y sobre todo para que veas **cómo se
sostiene**: qué autoriza cada flecha, qué línea de YAML creó cada caja y qué
hay de verdad en tu cuenta ahora mismo.

```bash
docker compose up
```

Y abre <http://localhost:8083>.

> Va en el **8083**: el 8080 es el simulador de reglas (clase 5), el 8081 el
> constructor de plantillas (clase 6) y el 8082 el panel (clase 7). Puedes
> tener los cuatro abiertos.

---

## Las tres vistas

### Arquitectura

El dibujo de todo lo que montaste, y **se enciende solo**. Cuando tu
dispositivo publica, las flechas de esa rama parpadean durante un segundo.

Lo importante es **qué rama no se enciende**. Si el nivel va bajo, la rama de
la alarma se queda apagada: ahí estás viendo un `WHERE` funcionar, no leyendo
sobre él.

Hay un interruptor, **«ver qué autoriza cada flecha»**, que reetiqueta todo el
dibujo con el permiso que hace posible cada paso: el certificado X.509 del
dispositivo, el rol de IAM de cada regla, la política de recurso de la Lambda,
y el «nadie» de la Function URL. Es la vista que explica por qué los tres tipos
de identidad del curso no son lo mismo.

> **Esto no espía el broker.** Mira lo que llegó a la tabla. Cada fila es la
> prueba de que la cadena entera funcionó: publicó el dispositivo, lo recibió
> IoT Core, encajó la regla y se escribió. Por eso hay un par de segundos de
> retraso, y por eso es información de verdad y no una animación decorativa.

### Servicios

Las mismas cajas en forma de ficha. Cada una abre con tres pestañas:

| Pestaña | Qué te da |
|---|---|
| **Qué es** | El servicio en dos frases, cómo lo usamos nosotros, y **lo que cuesta** |
| **Cómo lo creamos** | El bloque de `infra/laboratorio.yaml` que lo crea, **con sus comentarios**. No es un ejemplo: es tu plantilla |
| **Cómo está ahora** | Leído de tu cuenta, en solo lectura: si existe, cuántas filas tiene, si la regla está activa |

### Datos

Las últimas lecturas y un resumen con umbral, con su gráfico y su tabla.
Fíjate en las columnas: **ninguna está declarada en la plantilla salvo las dos
claves**. Aparecieron porque el dispositivo las mandó.

---

## La cruz roja no siempre es un fallo

La pestaña «cómo está ahora» busca los nombres **que dice la plantilla**. Si un
recurso existe pero lo creaste a mano en la consola con otro nombre, aquí sale
una cruz aunque funcione perfectamente.

Eso tiene nombre: **deriva**. Es la diferencia entre lo que tu arquitectura
*dice* y lo que tu cuenta *tiene*, y es exactamente el motivo por el que
conviene que todo salga de un archivo.

En la práctica te va a pasar con lo de las clases 3 a 5, que montaste a clics.

Y de paso es la herramienta de soporte: cuando alguien diga «a mí no me
funciona», abre esta vista y en cinco segundos ves en qué eslabón se rompió.

---

## Las credenciales

La plataforma **lee tu cuenta**, a diferencia del constructor de la clase 6.
Por eso conviene saber exactamente qué hace con tus claves:

- Monta `~/.aws` **en solo lectura** dentro del contenedor.
- Usa el perfil `curso`.
- **Las claves no bajan nunca al navegador.** La página le pregunta al
  servidor local, y el servidor habla con AWS. Es el mismo reparto que la
  Lambda de la clase 7, pero en tu laptop.
- Solo hace llamadas de lectura: `describe`, `list`, `get`, `query`. No crea,
  no modifica y no borra nada.

En Mac o Linux, cambia `${USERPROFILE}` por `${HOME}` en el `docker-compose.yml`.

---

## Si no hay cuenta, sigue funcionando

Si no encuentra credenciales, o la tabla no existe, arranca en **modo
demostración** con lecturas inventadas y lo dice con un aviso arriba. La
arquitectura y el YAML siguen siendo reales; lo único falso son los datos.

Es a propósito: el día que falle el wifi del aula, la clase continúa.

---

## Qué hay dentro

| Archivo | Qué hace |
|---|---|
| `arquitectura.py` | **El modelo**: qué cajas hay, cómo se unen, qué significa cada una y de qué recursos de la plantilla sale. Si quieres cambiar el dibujo, se cambia aquí |
| `servidor.py` | Sirve la página, lee la cuenta y empuja los eventos por SSE |
| `web/js/diagrama.js` | La geometría de las flechas |
| `web/js/app.js` | El pegamento |

El extractor de YAML **no usa un analizador**: recorta el texto por
indentación, a propósito. Un analizador devolvería la estructura y tiraría los
comentarios, que es justo lo que queremos enseñar.

---

## Para parar

```bash
docker compose down
```
