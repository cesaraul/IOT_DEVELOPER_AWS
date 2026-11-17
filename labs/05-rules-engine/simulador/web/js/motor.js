// El motor de reglas: lo que hace AWS por dentro, en pequeño.
//
// POR QUÉ ESTE ARCHIVO EXISTE Y QUÉ NO ES
//   Esto NO es AWS. Es una imitación deliberadamente pequeña del Rules
//   Engine, para que puedas ver en tu pantalla qué le pasa a cada mensaje
//   sin gastar un centavo ni esperar a que algo se propague.
//
//   Pero tiene una regla de oro: **todo lo que se puede armar aquí tiene
//   que ser válido en AWS de verdad**. Un simulador que acepte cosas que
//   la consola luego rechaza enseña mentiras, y eso es peor que no tener
//   simulador. Por eso los bloques solo ofrecen construcciones reales, y
//   por eso la consulta se escribe en pantalla mientras la armas: lo que
//   armes aquí lo puedes copiar y pegar allá.
//
// LO QUE SÍ ESTÁ
//   FROM con comodines + y #, WHERE con una condición, SELECT de campos
//   o de todo, y las funciones topic() y timestamp().
//
// LO QUE NO ESTÁ, Y EN AWS TAMPOCO
//   JOIN, tablas, subconsultas. El FROM de una regla es un topic, no una
//   tabla, y no hay nada guardado contra lo que cruzar datos.

// ---------------------------------------------------------------------------
// 1. ¿Encaja el topic del mensaje con el filtro de la regla?
// ---------------------------------------------------------------------------
// Son las mismas reglas de comodines de MQTT que vimos en la clase 2:
//   +   un nivel exacto, el que sea
//   #   de aquí hasta el final (solo al final del filtro)

export function topicEncaja(filtro, topic) {
  const f = filtro.split("/");
  const t = topic.split("/");

  for (let i = 0; i < f.length; i++) {
    if (f[i] === "#") return true;        // comodín de cola: todo lo demás vale
    if (i >= t.length) return false;      // el topic se acabó antes que el filtro
    if (f[i] === "+") continue;           // este nivel da igual
    if (f[i] !== t[i]) return false;      // un nivel que no coincide: fuera
  }

  return f.length === t.length;
}

// ---------------------------------------------------------------------------
// 2. ¿Cumple el mensaje la condición del WHERE?
// ---------------------------------------------------------------------------

export function cumpleCondicion(condicion, datos) {
  // Sin WHERE, pasan todos los mensajes. Es lo mismo que en AWS.
  if (!condicion || !condicion.campo) return true;

  const valor = datos[condicion.campo];

  // Un campo que el mensaje no trae NO cumple la condición. Tampoco falla:
  // simplemente no encaja. En AWS pasa igual, y es una fuente de confusión
  // clásica cuando un dispositivo cambia su payload y nadie se entera.
  if (valor === undefined) return false;

  const esperado = condicion.valor;

  switch (condicion.operador) {
    case "=":  return valor === esperado;
    case "<>": return valor !== esperado;
    case ">":  return Number(valor) > Number(esperado);
    case "<":  return Number(valor) < Number(esperado);
    case ">=": return Number(valor) >= Number(esperado);
    case "<=": return Number(valor) <= Number(esperado);
    default:   return false;
  }
}

// ---------------------------------------------------------------------------
// 3. ¿Qué parte del mensaje se lleva el SELECT?
// ---------------------------------------------------------------------------

export function aplicarSelect(seleccion, datos, topic) {
  // SELECT * se lleva el mensaje entero, tal cual llegó.
  if (seleccion.todo) {
    var salida = Object.assign({}, datos);
  } else {
    var salida = {};
    for (const campo of seleccion.campos) {
      if (datos[campo] !== undefined) salida[campo] = datos[campo];
    }
  }

  // Y aquí está lo que más sorprende la primera vez: la consulta puede
  // AÑADIR cosas que el mensaje no traía. El dispositivo manda lo mínimo
  // (cada byte se paga en una red celular o satelital) y la nube completa.
  if (seleccion.anadeDispositivo) {
    salida.dispositivo = topic.split("/")[2] || "";   // topic(3) en AWS
  }
  if (seleccion.anadeHora) {
    salida.recibido = Date.now();                     // timestamp() en AWS
  }

  return salida;
}

// ---------------------------------------------------------------------------
// 4. Evaluar un mensaje contra una regla
// ---------------------------------------------------------------------------
// Devuelve siempre un veredicto, incluso cuando el mensaje se descarta: en
// este simulador nos interesa tanto lo que pasa como lo que NO pasa, porque
// en AWS lo que no encaja desaparece sin dejar rastro.

export function evaluar(regla, topic, datos) {
  if (!topicEncaja(regla.desde, topic)) {
    return { encaja: false, motivo: "otro topic" };
  }

  if (!cumpleCondicion(regla.condicion, datos)) {
    return { encaja: false, motivo: "no cumple el WHERE" };
  }

  return { encaja: true, resultado: aplicarSelect(regla.seleccion, datos, topic) };
}

// ---------------------------------------------------------------------------
// 5. Escribir la consulta SQL de verdad
// ---------------------------------------------------------------------------
// Esta función es el puente entre el juguete y AWS. Lo que devuelve aquí se
// puede pegar tal cual en la consola. Si algún día cambias los bloques,
// cambia también esto: el día que dejen de coincidir, el simulador empieza
// a enseñar cosas que no son.

function comoValorSQL(valor) {
  if (typeof valor === "string") return `'${valor}'`;
  return String(valor);
}

export function escribirSQL(regla) {
  const partes = [];

  if (regla.seleccion.todo) {
    partes.push("*");
  } else {
    partes.push(...regla.seleccion.campos);
  }

  if (regla.seleccion.anadeDispositivo) partes.push("topic(3) AS dispositivo");
  if (regla.seleccion.anadeHora) partes.push("timestamp() AS recibido");

  // SELECT sin nada seleccionado no existe en AWS: hay que pedir algo.
  const campos = partes.length ? partes.join(", ") : "*";

  let sql = `SELECT ${campos}\nFROM '${regla.desde}'`;

  const c = regla.condicion;
  if (c && c.campo) {
    sql += `\nWHERE ${c.campo} ${c.operador} ${comoValorSQL(c.valor)}`;
  }

  return sql;
}
