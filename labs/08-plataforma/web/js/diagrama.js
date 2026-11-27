// Geometría: lo único de esta herramienta que tiene algo de matemática.

// El camino de una flecha entre dos cajas.
//
// Hacia adelante (de izquierda a derecha) va en codo: sale por el lado
// derecho, se desplaza hasta la mitad, sube o baja, y entra por el lado
// izquierdo. Hacia atrás —la API, que está abajo y lee de los almacenes,
// que están arriba— sube por un pasillo libre a la derecha y entra por
// el lado derecho del destino.
export function ruta(a, b, i = 0) {
  const ax = a.x + a.w, ay = a.y + a.h / 2;
  const by = b.y + b.h / 2;

  if (b.x >= ax) {
    if (Math.abs(ay - by) < 2) return `M${ax} ${ay} H${b.x}`;
    // El desplazamiento por índice evita que dos flechas que salen de
    // la misma caja se pisen en el tramo vertical.
    const m = ax + (b.x - ax) / 2 + (i % 3) * 9;
    return `M${ax} ${ay} H${m} V${by} H${b.x}`;
  }

  const pasillo = 876 + (i % 3) * 16;
  return `M${ax} ${ay} H${pasillo} V${by} H${b.x + b.w}`;
}

// Punto medio del camino, para colgar ahí la etiqueta.
export function medio(a, b) {
  const ax = a.x + a.w, ay = a.y + a.h / 2;
  const by = b.y + b.h / 2;
  if (b.x >= ax) return { x: ax + (b.x - ax) / 2, y: (ay + by) / 2 - 7 };
  return { x: 876, y: (ay + by) / 2 };
}

// Una línea en SVG con los niveles que han ido llegando. Sin librerías.
export function curva(filas, ancho = 640, alto = 150) {
  const v = filas
    .map((f) => ({ x: f.momento, y: Number(f.nivel) }))
    .filter((p) => !isNaN(p.y));
  if (v.length < 2) return null;

  const ys = v.map((p) => p.y);
  let min = Math.min(...ys), max = Math.max(...ys);
  if (max - min < 1) max = min + 1;

  const m = 12;
  const px = (i) => m + (i * (ancho - 2 * m)) / (v.length - 1);
  const py = (y) => alto - m - ((y - min) * (alto - 2 * m)) / (max - min);

  return {
    linea: v.map((p, i) => `${px(i).toFixed(1)},${py(p.y).toFixed(1)}`).join(" "),
    min, max, alto, ancho, enY: py,
    desde: v[0].x, hasta: v[v.length - 1].x,
  };
}

// DynamoDB devuelve ordenado; S3 no. Ordenar aquí no es un detalle de
// programación: es la diferencia entre las dos formas de guardar.
export function ordenar(filas) {
  return [...filas].sort((a, b) =>
    String(a.momento).localeCompare(String(b.momento)));
}
