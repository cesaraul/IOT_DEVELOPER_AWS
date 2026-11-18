# Simulador del Rules Engine

Un banco de pruebas para entender **qué es una regla** antes de tocar AWS.
Armas la regla con bloques, ves qué mensajes pasan y cuáles se descartan, y
eliges qué pasa con los que pasan.

```bash
docker compose up
```

Y abre <http://localhost:8080>.

No necesita cuenta de AWS, no cuesta nada y se puede romper todas las veces
que haga falta.

---

## Esto NO es AWS

Es una imitación pequeña, hecha para aprender. Lo que construyes de verdad va
en la consola, después.

Pero tiene una regla de oro: **todo lo que se puede armar aquí es válido en
AWS**. Los bloques solo ofrecen construcciones reales, y la consulta se
escribe en pantalla mientras la armas:

```sql
SELECT nivel, temp
FROM 'fablab/planta1/+/telemetria'
WHERE alarma = true
```

Eso se copia y se pega tal cual en **IoT Core → Enrutamiento de mensajes →
Reglas**. El simulador no es una metáfora de una regla: es una regla.

---

## Qué hay dentro

| Servicio | Qué es | En AWS sería |
|---|---|---|
| `broker` | Mosquitto en tu laptop | AWS IoT Core |
| `dispositivo` | Un tanque con una bomba | Tu Thing de la clase 3 |
| `web` | La interfaz | — |

El **motor de reglas y las tres funciones corren en tu navegador**, no en un
servidor. Por eso la interfaz no tiene nada que construir ni dependencias que
instalar: son archivos estáticos.

El dispositivo publica **exactamente el mismo payload** que el de la clase 4:

```json
{"nivel": 72.4, "temp": 24.1, "alarma": false}
```

Lo único que cambia es con quién habla: aquí un broker local sin
certificados, allá AWS por TLS. El código de AWS no se toca.

---

## El guion, en cuatro pasos

Este es el recorrido para el que está hecho. Son unos 15 minutos.

### 1 · Qué hace cada parte de la consulta

Arranca con la regla por defecto. Mira la lista «mensaje a mensaje»: lo verde
salió por el otro lado, lo gris **no existe en ninguna parte**.

Fíjate en lo que sale: `{"nivel":91.2,"temp":28.4}`. **`alarma` no está.** Se
usó para decidir, no para llevárselo. Eso es el `SELECT`.

Prueba a cambiar el `FROM` a `fablab/planta2/...`: no llega nada. El topic
tiene que encajar, y el `+` es el comodín de MQTT de la clase 2.

### 2 · La regla no recuerda nada

Pon la acción en **Mandar correo** y deja que el nivel suba.

El contador de correos sube **y no para**. Cada mensaje de alarma manda uno
nuevo, porque la regla no sabe que ya avisó. Con un equipo publicando cada 2
segundos, diez minutos de alarma son 300 correos.

**Eso es lo que una regla no puede hacer.**

### 3 · Para eso está Lambda

Cambia la acción a **Llamar a una Lambda** → *Avisa una sola vez*.

Un correo. Uno. La función guarda que ya avisó, y la regla sigue haciendo su
trabajo igual que antes. Debajo tienes el código Python que escribirías en la
consola de verdad.

### 4 · Cerrar el lazo

Cambia a **Apaga la bomba**.

Cuando el nivel pasa de 90, la función **escribe el estado deseado** del
dispositivo. El equipo lo lee, apaga la bomba, y **el nivel empieza a bajar
en la barra**.

Nadie intervino: el dato entró, se decidió y se actuó. Es el shadow de la
clase 4 enganchado con la regla de hoy, y es el sistema completo.

---

## Un error que el simulador también comete

Si pones `FROM 'fablab/#'` y republicas dentro de `fablab/...`, la regla se
alimenta de su propia salida. Aquí lo evitamos a mano, pero **en AWS pasa de
verdad**: una regla que se dispara con su propio mensaje, para siempre, y la
factura la pagas tú. Es uno de los errores caros clásicos del Rules Engine.

---

## Para parar todo

```bash
docker compose down
```
