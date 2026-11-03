/* Estado compartido de la interfaz.
 *
 * Un único objeto reactivo: los componentes lo leen y Vue se encarga de
 * repintar lo que cambió. Aquí dentro entran dos cosas:
 *   - lo que empuja el servidor por WebSocket (paquetes, avisos, latencias)
 *   - lo que se consulta una vez por segundo (métricas consolidadas)
 */

const tienda = Vue.reactive({
  vista: "http-pasos",
  conexion: "conectando",

  estado: {
    metricas: {
      http: { mensajes: 0, bytes_total: 0, bytes_utiles: 0, errores: 0, reintentos: 0,
              polls: 0, bytes_polling: 0, eficiencia: 0, bytes_por_mensaje: 0, mb_por_mes: 0 },
      mqtt: { mensajes: 0, bytes_total: 0, bytes_utiles: 0, errores: 0, reintentos: 0,
              eficiencia: 0, bytes_por_mensaje: 0, mb_por_mes: 0 },
    },
    topics: {},
    fallos: { tasa_503: 0, tasa_429: 0, latencia_ms: 0, red_caida: false },
    base_topic: "fablab/planta1/tanque-03",
    config: { intervalo_s: 5 },
    intervalo_mqtt: 5,
  },

  paquetes: [],
  avisos: [],
  latencias: [],
  estadoDispositivo: "—",
  pausa: false,
  filtro: "todos",
  cronometros: { http: "—", mqtt: "—" },
});

// ------------------------------------------------------------ utilidades

const util = {
  bytes(n) {
    if (n === undefined || n === null) return "—";
    if (n < 1024) return `${Math.round(n)} B`;
    if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / 1048576).toFixed(2)} MB`;
  },
  hora() {
    return new Date().toLocaleTimeString("es-PE", { hour12: false });
  },
  /** Reglas de + y # de MQTT, para resaltar coincidencias en la interfaz. */
  coincideTopic(patron, topic) {
    const p = patron.split("/");
    const t = topic.split("/");
    for (let i = 0; i < p.length; i++) {
      if (p[i] === "#") return true;
      if (i >= t.length) return false;
      if (p[i] !== "+" && p[i] !== t[i]) return false;
    }
    return p.length === t.length;
  },
  async enviar(ruta, cuerpo) {
    return fetch(ruta, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo || {}),
    });
  },
};

// ------------------------------------------------------------ WebSocket

let temporizadorCrono = {};

function arrancarCronometro(via) {
  const inicio = performance.now();
  clearInterval(temporizadorCrono[via]);
  temporizadorCrono[via] = setInterval(() => {
    tienda.cronometros[via] = `${((performance.now() - inicio) / 1000).toFixed(1)} s`;
  }, 100);
}

function pararCronometro(via, texto) {
  clearInterval(temporizadorCrono[via]);
  tienda.cronometros[via] = texto;
}

function conectarEventos() {
  const socket = new WebSocket(`ws://${location.host}/ws`);

  socket.onopen = () => (tienda.conexion = "en vivo");
  socket.onclose = () => {
    tienda.conexion = "sin conexión";
    setTimeout(conectarEventos, 2000);
  };

  socket.onmessage = (mensaje) => {
    const ev = JSON.parse(mensaje.data);
    switch (ev.tipo) {
      case "paquete":
        if (tienda.pausa) break;
        ev.clave = `${ev.ts}-${Math.random()}`;
        ev.abierto = false;
        tienda.paquetes.unshift(ev);
        if (tienda.paquetes.length > 60) tienda.paquetes.pop();
        break;
      case "aviso":
        tienda.avisos.unshift({ ...ev, hora: util.hora(), clave: `${ev.ts}-${Math.random()}` });
        if (tienda.avisos.length > 200) tienda.avisos.pop();
        break;
      case "latencia":
        pararCronometro(ev.via, `${(ev.latencia_ms / 1000).toFixed(2)} s`);
        tienda.latencias.unshift({ ...ev, hora: util.hora() });
        if (tienda.latencias.length > 30) tienda.latencias.pop();
        break;
      case "estado_dispositivo":
        tienda.estadoDispositivo = ev.valor;
        tienda.avisos.unshift({
          texto: `topic ${ev.topic} → "${ev.valor}"${ev.retenido ? " (retenido)" : ""}`,
          nivel: ev.valor === "online" ? "ok" : "error",
          hora: util.hora(),
          clave: `${ev.ts}-${Math.random()}`,
        });
        break;
      case "reset":
        tienda.paquetes = [];
        tienda.latencias = [];
        break;
    }
  };
}

async function refrescarEstado() {
  try {
    const r = await fetch("/api/estado");
    Object.assign(tienda.estado, await r.json());
  } catch (error) {
    /* el servidor se está reiniciando; se reintenta al siguiente segundo */
  }
}
