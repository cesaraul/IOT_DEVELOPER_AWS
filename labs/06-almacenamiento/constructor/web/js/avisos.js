// Los avisos cruzados.
//
// POR QUÉ ESTE ARCHIVO ES EL MÁS IMPORTANTE DE LA HERRAMIENTA
//   Leer una plantilla no enseña lo que de verdad cuesta entender: que los
//   recursos se necesitan entre sí. La tabla espera unos campos que tiene
//   que producir la regla. El rol tiene que permitir exactamente lo que la
//   regla intenta hacer. Si una pieza cambia, otra deja de encajar.
//
//   Eso es invisible cuando el YAML ya está escrito y funciona. Aquí se ve,
//   porque al cambiar una decisión aparece el aviso al instante.
//
//   Ninguno bloquea nada. Puedes desplegar una plantilla rota a propósito:
//   es tu cuenta, son datos de prueba, y equivocarse es la parte barata de
//   aprender.

// Lo que esperan los scripts del laboratorio. Si cambias las claves, esto
// deja de cuadrar — y es un acoplamiento real, no una limitación nuestra.
const CLAVE_ESPERADA = "dispositivo";
const ORDEN_ESPERADO = "momento";

export function calcularAvisos(e) {
  const avisos = [];

  // --- La regla no produce lo que la tabla necesita --------------------
  if (e.aDynamo && !e.anadeDispositivo) {
    avisos.push({
      nivel: "grave",
      texto:
        `La tabla usa «${e.clavePart}» como clave de partición, pero tu regla ` +
        `no lo produce. El mensaje del dispositivo trae nivel, temp y alarma: ` +
        `«${e.clavePart}» tiene que añadirlo la consulta con topic(3). ` +
        `Sin eso, DynamoDB rechaza cada fila.`,
    });
  }

  if (e.aDynamo && e.claveOrden && !e.anadeMomento) {
    avisos.push({
      nivel: "grave",
      texto:
        `Lo mismo con «${e.claveOrden}»: es la clave de ordenación y nadie ` +
        `la está generando. Actívala en la regla o quítala de la tabla.`,
    });
  }

  // --- El tipo no cuadra con lo que produce la consulta ----------------
  if (e.aDynamo && e.anadeMomento && e.tipoOrden === "N") {
    avisos.push({
      nivel: "grave",
      texto:
        `parse_time devuelve TEXTO, pero declaraste «${e.claveOrden}» como ` +
        `número. DynamoDB rechazará la fila por el tipo. Ponlo como texto, o ` +
        `usa timestamp() en vez de parse_time.`,
    });
  }

  // --- Filtrar lo que se guarda ----------------------------------------
  if (e.conWhere) {
    avisos.push({
      nivel: "ojo",
      texto:
        "Le pusiste WHERE a la regla de guardar. Se filtra lo que se avisa, " +
        "no lo que se guarda: el dato que descartes hoy no se recupera mañana. " +
        "Para avisar ya tienes la regla de la clase 5.",
    });
  }

  // --- Costo -------------------------------------------------------------
  if (e.aDynamo && e.capacidad === "bajo-demanda") {
    avisos.push({
      nivel: "ojo",
      texto:
        "Bajo demanda se paga desde la primera escritura: el Free Tier " +
        "permanente de DynamoDB (25 unidades) solo cubre el modo aprovisionado. " +
        "En el curso son céntimos, pero conviene saberlo.",
    });
  }

  // --- Acoplamiento con los scripts --------------------------------------
  if (e.aDynamo && e.clavePart !== CLAVE_ESPERADA) {
    avisos.push({
      nivel: "ojo",
      texto:
        `consultar.py busca la clave «${CLAVE_ESPERADA}». La llamaste ` +
        `«${e.clavePart}», así que ese script dejará de encontrar tus filas. ` +
        `No está mal: es lo que pasa cuando cambias la infraestructura y no el código.`,
    });
  }

  if (e.aDynamo && e.claveOrden && e.claveOrden !== ORDEN_ESPERADO) {
    avisos.push({
      nivel: "ojo",
      texto:
        `consultar.py --rango usa «${ORDEN_ESPERADO}» para buscar entre dos ` +
        `horas. Con «${e.claveOrden}» habría que cambiar también el script.`,
    });
  }

  // --- Reemplazo de la tabla ---------------------------------------------
  if (e.yaDesplegado && e.aDynamo) {
    avisos.push({
      nivel: "ojo",
      texto:
        "Si ya desplegaste esta pila y ahora cambias una clave, CloudFormation " +
        "no modifica la tabla: la borra y crea otra, con los datos dentro. " +
        "Míralo en la columna «Reemplazo» del conjunto de cambios antes de aplicar.",
    });
  }

  // --- Sin destinos --------------------------------------------------------
  if (!e.aDynamo && !e.aS3) {
    avisos.push({
      nivel: "grave",
      texto:
        "No elegiste ningún destino. La regla se dispararía con cada mensaje " +
        "y no haría nada con él.",
    });
  }

  // --- Todo en orden -------------------------------------------------------
  if (!avisos.length) {
    avisos.push({
      nivel: "bien",
      texto:
        "Las piezas encajan: la regla produce los campos que la tabla usa como " +
        "clave, y el rol permite exactamente lo que la regla intenta hacer.",
    });
  }

  return avisos;
}
