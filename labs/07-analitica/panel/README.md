# El panel

```bash
docker compose up
```

Y abre <http://localhost:8082>.

> Va en el **8082**: el 8080 es el simulador de reglas (clase 5) y el 8081
> el constructor de plantillas (clase 6). Puedes tener los tres abiertos.

---

## Lo que hay aquí dentro, y lo que no

**No hay credenciales de AWS.** No las pide, no las guarda y no las
necesita. Tampoco hay un `Dockerfile`: es un nginx sirviendo archivos
estáticos, nada más.

Quien habla con AWS es **tu Lambda**, al otro lado de la dirección que
pegas en la página. Eso no es una simplificación para la clase: es como
se construyen las aplicaciones de verdad. Las claves nunca bajan al
navegador.

La dirección de tu API se queda en el `localStorage` de ese navegador,
para no tener que pegarla cada vez.

---

## Por dónde mirar

| Archivo | Qué hace |
|---|---|
| `web/js/consulta.js` | Convierte la pregunta en una dirección HTTP. Es la pieza que importa |
| `web/js/app.js` | El pegamento: pide, cronometra y pinta |
| `web/index.html` | La página |
| `web/css/estilo.css` | Los colores, en claro y en oscuro |

En `consulta.js` están las dos cosas que más se preguntan en clase:

- **Por qué se convierte la hora.** El `momento` que guardó la regla es la
  hora del servidor, en UTC. El campo del navegador da hora local. Sin la
  conversión, en Lima preguntarías por una ventana corrida cinco horas y
  parecería que no hay datos.

- **Por qué se ordenan las filas de S3.** DynamoDB las devuelve ordenadas
  porque tiene una clave de ordenación. S3 devuelve **archivos**, con un
  `uuid` por nombre, en cualquier orden. Ordenar aquí no es un detalle de
  programación: es la diferencia entre las dos formas de guardar.

---

## Para parar

```bash
docker compose down
```
