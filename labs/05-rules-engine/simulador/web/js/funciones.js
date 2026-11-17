// Las tres funciones Lambda del simulador.
//
// POR QUÉ TRES, Y POR QUÉ ESTAS TRES
//   Cada una responde a una cosa que una regla NO puede hacer. Esa es toda
//   la razón de ser de Lambda, y por eso aquí no hay una función que haga
//   algo que la regla ya sabía hacer sola: no enseñaría nada.
//
//   1. recordar       -> la regla no tiene memoria entre mensajes
//   2. completar      -> la regla no puede consultar nada fuera del mensaje
//   3. decidir y actuar -> la regla no puede escribir en el shadow
//
// EL CÓDIGO QUE SE MUESTRA
//   Cada función trae su equivalente en Python, el que escribirías de
//   verdad en la consola de AWS. Aquí corre en JavaScript porque esto vive
//   en tu navegador, pero lo que lee el alumno es Python, que es lo que va
//   a escribir el día que lo haga en serio.

export const FUNCIONES = [
  // -------------------------------------------------------------------------
  {
    id: "avisa_una_vez",
    nombre: "Avisa una sola vez",
    resuelve: "La regla no recuerda. Esta sí.",
    explicacion:
      "Guarda si ya avisó. El primer mensaje de alarma manda el aviso; " +
      "los siguientes no hacen nada. Es la respuesta directa a los 300 correos.",
    codigo: `avisado = False          # vive entre ejecuciones

def lambda_handler(event, context):
    global avisado

    if avisado:
        print("ya avisé, no repito")
        return

    avisado = True
    enviar_correo(f"Alarma: nivel {event['nivel']}")`,

    estadoInicial: () => ({ avisado: false }),

    ejecutar(evento, estado, ctx) {
      if (estado.avisado) {
        ctx.log("ya avisé antes, no repito");
        return;
      }
      estado.avisado = true;
      ctx.avisar(`Alarma: nivel ${evento.nivel ?? "?"}`);
      ctx.log("primer aviso enviado");
    },
  },

  // -------------------------------------------------------------------------
  {
    id: "completa_el_dato",
    nombre: "Completa y guarda",
    resuelve: "La regla no sabe nada fuera del mensaje.",
    explicacion:
      "Le añade el nombre del equipo y la hora, decide si es grave, y lo " +
      "guarda en una tabla. El dispositivo manda lo mínimo; la nube completa.",
    codigo: `import time

def lambda_handler(event, context):
    fila = dict(event)
    fila["dispositivo"] = event.get("dispositivo", "desconocido")
    fila["hora"] = time.strftime("%H:%M:%S")
    fila["gravedad"] = "alta" if event.get("nivel", 0) > 90 else "media"

    guardar_en_tabla(fila)`,

    estadoInicial: () => ({}),

    ejecutar(evento, estado, ctx) {
      const fila = Object.assign({}, evento);
      fila.dispositivo = evento.dispositivo || ctx.dispositivo || "desconocido";
      fila.hora = new Date().toLocaleTimeString("es-PE", { hour12: false });
      fila.gravedad = (evento.nivel ?? 0) > 90 ? "alta" : "media";

      ctx.guardar(fila);
      ctx.log(`guardada una fila (gravedad ${fila.gravedad})`);
    },
  },

  // -------------------------------------------------------------------------
  {
    id: "cierra_el_lazo",
    nombre: "Apaga la bomba",
    resuelve: "La regla no puede escribir en el shadow.",
    explicacion:
      "Mira el nivel y, si se pasa, escribe el estado deseado del " +
      "dispositivo. El equipo lo lee y apaga la bomba él mismo. Nadie " +
      "intervino: el dato entró, se decidió y se actuó.",
    codigo: `import json, boto3

iot = boto3.client("iot-data")

def lambda_handler(event, context):
    if event.get("nivel", 0) <= 90:
        return

    iot.update_thing_shadow(
        thingName=event["dispositivo"],
        payload=json.dumps({
            "state": {"desired": {"bomba": "apagada"}}
        }),
    )`,

    estadoInicial: () => ({ apagada: false }),

    ejecutar(evento, estado, ctx) {
      const nivel = evento.nivel ?? 0;

      if (nivel <= 90) {
        ctx.log(`nivel ${nivel}: todavía no hace falta`);
        return;
      }

      if (estado.apagada) {
        ctx.log("ya pedí apagarla");
        return;
      }

      estado.apagada = true;
      ctx.escribirShadow({ bomba: "apagada" });
      ctx.log("escrito desired = {bomba: apagada}");
      ctx.avisar("La bomba se apagó sola");
    },
  },
];

export function buscarFuncion(id) {
  return FUNCIONES.find((f) => f.id === id) || null;
}
