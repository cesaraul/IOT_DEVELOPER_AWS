// Aquí se arma la pregunta. Nada más.
//
// Un panel de datos no es más que esto: convertir lo que alguien quiere
// saber en una dirección HTTP, y pintar lo que vuelve. Todo el trabajo
// de verdad —buscar entre las filas— lo hace la Lambda, que está al otro
// lado y tiene los permisos para leer.

// ---------------------------------------------------------------------
//  Las cuatro preguntas que la API sabe responder
// ---------------------------------------------------------------------
//  No son cuatro al azar: dos de ellas van a DynamoDB y una va a S3,
//  que es exactamente la distinción de la clase 6. La cuarta, el
//  resumen, es la única que no devuelve datos sino una conclusión.
// ---------------------------------------------------------------------

export const PREGUNTAS = [
  {
    id: "ultimas",
    titulo: "¿Cómo está ahora?",
    pie: "Las últimas lecturas, de la más reciente a la más vieja.",
    fuente: "DynamoDB",
    campos: ["n"],
  },
  {
    id: "rango",
    titulo: "¿Qué pasó entre estas dos horas?",
    pie: "Una ventana de tiempo. Esto es lo que la clave de ordenación hace posible.",
    fuente: "DynamoDB",
    campos: ["desde", "hasta", "n"],
  },
  {
    id: "resumen",
    titulo: "¿Cuántas veces pasó del umbral?",
    pie: "Las mismas filas, pero la Lambda las cuenta y devuelve el resultado.",
    fuente: "DynamoDB",
    campos: ["desde", "hasta", "umbral", "n"],
  },
  {
    id: "dia",
    titulo: "¿Y el día completo?",
    pie: "Desde el histórico de S3: los archivos que la regla fue dejando ese día.",
    fuente: "S3",
    campos: ["fecha"],
  },
];

// ---------------------------------------------------------------------
//  De las decisiones a los parámetros
// ---------------------------------------------------------------------
//  Se devuelve una lista en vez de un objeto para poder enseñarlos en
//  pantalla uno por línea, con su explicación al lado. Ver la dirección
//  formarse es la mitad de la clase.
// ---------------------------------------------------------------------

export function parametros(e) {
  const p = [["accion", e.accion, "qué le estás preguntando"]];

  p.push(["dispositivo", e.dispositivo, "la clave de partición: DE QUIÉN"]);

  const campos = PREGUNTAS.find((q) => q.id === e.accion).campos;

  if (campos.includes("desde") && e.desde) {
    p.push(["desde", aIso(e.desde), "la clave de ordenación: DESDE CUÁNDO"]);
  }
  if (campos.includes("hasta") && e.hasta) {
    p.push(["hasta", aIso(e.hasta), "…y hasta cuándo"]);
  }
  if (campos.includes("umbral")) {
    p.push(["umbral", e.umbral, "lo decide quien pregunta, no el dispositivo"]);
  }
  if (campos.includes("fecha")) {
    p.push(["fecha", e.fecha.replaceAll("-", "/"), "así están las carpetas en el bucket"]);
  }
  if (campos.includes("n")) {
    p.push(["n", e.n, "cuántas filas como máximo"]);
  }
  return p;
}

// El dato que guarda la regla es la hora del SERVIDOR, en UTC. El
// campo del navegador da hora local. Si no se convierte, en Lima se
// preguntaría por una ventana corrida cinco horas y "no hay datos".
function aIso(local) {
  const d = new Date(local);
  return isNaN(d) ? "" : d.toISOString();
}

export function construirUrl(base, e) {
  if (!base) return "";
  const q = parametros(e)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join("&");
  return `${base.replace(/\/+$/, "")}/?${q}`;
}

export function construirCurl(base, e) {
  const url = construirUrl(base, e);
  return url ? `curl.exe -s "${url}"` : "";
}

// ---------------------------------------------------------------------
//  Lo que vuelve
// ---------------------------------------------------------------------

// DynamoDB devuelve las filas ya ordenadas: para eso existe la clave de
// ordenación. S3 devuelve ARCHIVOS, y los nombra con un uuid al azar,
// así que llegan en cualquier orden. Ordenar aquí no es un detalle de
// programación: es la diferencia entre las dos formas de guardar.
export function ordenar(filas) {
  return [...filas].sort((a, b) => String(a.momento).localeCompare(String(b.momento)));
}

// Una línea en SVG, sin librerías. Devuelve también los extremos para
// poder rotular el eje.
export function curva(filas, ancho = 640, alto = 150) {
  const v = filas
    .map((f) => ({ x: f.momento, y: Number(f.nivel) }))
    .filter((p) => !isNaN(p.y));

  if (v.length < 2) return null;

  const ys = v.map((p) => p.y);
  let min = Math.min(...ys);
  let max = Math.max(...ys);
  if (max - min < 1) { max = min + 1; }        // una línea plana sigue siendo una línea

  const margen = 12;
  const px = (i) => margen + (i * (ancho - 2 * margen)) / (v.length - 1);
  const py = (y) => alto - margen - ((y - min) * (alto - 2 * margen)) / (max - min);

  return {
    linea: v.map((p, i) => `${px(i).toFixed(1)},${py(p.y).toFixed(1)}`).join(" "),
    min, max, alto, ancho,
    enY: (y) => py(y),
    desde: v[0].x,
    hasta: v[v.length - 1].x,
  };
}
