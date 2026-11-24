// El pegamento: recoge la pregunta, la manda, cronometra y pinta.

import { PREGUNTAS, parametros, construirUrl, construirCurl, ordenar, curva }
  from "./consulta.js";

const { createApp } = Vue;

// Hoy a las 00:00 y ahora, en el formato que pide <input datetime-local>.
function local(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}` +
         `T${p(d.getHours())}:${p(d.getMinutes())}`;
}

const ahora = new Date();
const medianoche = new Date(ahora);
medianoche.setHours(0, 0, 0, 0);

createApp({
  data() {
    return {
      preguntas: PREGUNTAS,
      tamano: 100,

      // La dirección de TU Lambda. Sale de los Outputs de la pila y se
      // queda guardada en este navegador, no en ningún servidor.
      base: localStorage.getItem("api-clase7") || "",

      e: {
        accion: "ultimas",
        dispositivo: "demo-clase3",
        n: 50,
        desde: local(medianoche),
        hasta: local(ahora),
        umbral: 90,
        fecha: local(ahora).slice(0, 10),
      },

      pidiendo: false,
      error: "",
      respuesta: null,
      ms: 0,
      loQuePregunte: "",     // la acción que de verdad contestó
    };
  },

  computed: {
    pregunta() {
      return PREGUNTAS.find((q) => q.id === this.e.accion);
    },

    campos() {
      return this.pregunta.campos;
    },

    partes() {
      return parametros(this.e);
    },

    url() {
      return construirUrl(this.base, this.e);
    },

    curl() {
      return construirCurl(this.base, this.e);
    },

    // En DynamoDB vienen ordenadas; las de S3 hay que ordenarlas aquí.
    filas() {
      if (!this.respuesta) return [];
      const f = this.respuesta.filas || this.respuesta.datos || [];
      return ordenar(f);
    },

    resumen() {
      return this.respuesta && this.respuesta.resumen;
    },

    // Las columnas no están declaradas en ningún sitio: se descubren
    // mirando lo que llegó. Eso es porque la tabla es sin esquema, y
    // también por qué un panel genérico puede existir.
    columnas() {
      const vistas = [];
      for (const f of this.filas) {
        for (const k of Object.keys(f)) if (!vistas.includes(k)) vistas.push(k);
      }
      const primero = ["momento", "dispositivo", "nivel"];
      return [...primero.filter((k) => vistas.includes(k)),
              ...vistas.filter((k) => !primero.includes(k))];
    },

    grafico() {
      return curva(this.filas);
    },

    // Para dibujar la línea del umbral dentro del gráfico.
    yUmbral() {
      const g = this.grafico;
      if (!g || !this.resumen) return null;
      const u = Number(this.resumen.umbral);
      if (u < g.min || u > g.max) return null;      // fuera del cuadro
      return g.enY(u);
    },
  },

  watch: {
    base(v) {
      localStorage.setItem("api-clase7", v.trim());
    },
  },

  methods: {
    ajustar(delta) {
      this.tamano = Math.min(170, Math.max(70, this.tamano + delta));
      document.getElementById("app").style.zoom = this.tamano / 100;
    },

    async preguntar() {
      if (!this.base) { this.error = "Falta la dirección de tu API."; return; }

      this.pidiendo = true;
      this.error = "";
      this.respuesta = null;
      const reloj = performance.now();

      try {
        const r = await fetch(this.url);
        const datos = await r.json();
        this.ms = Math.round(performance.now() - reloj);
        this.loQuePregunte = this.e.accion;

        // Una Lambda que falla igual contesta: con 500 y el motivo
        // dentro. Enseñarlo tal cual es más útil que un "error".
        if (datos.error) { this.error = datos.error; return; }

        this.respuesta = datos;
      } catch (e) {
        this.ms = Math.round(performance.now() - reloj);
        this.error =
          `No llegué a la API (${e.message}). Revisa que la dirección esté ` +
          `completa y que la pila clase7 siga desplegada.`;
      } finally {
        this.pidiendo = false;
      }
    },

    corto(v) {
      if (typeof v === "string" && v.length > 26) return v.slice(0, 26) + "…";
      return v;
    },

    hora(iso) {
      // El dato está en UTC; se enseña en la hora de quien mira.
      const d = new Date(iso);
      return isNaN(d) ? iso : d.toLocaleTimeString();
    },
  },
}).mount("#app");
