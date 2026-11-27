// El pegamento: pide el modelo, dibuja, escucha los eventos y abre el
// detalle de cada caja.

import { ruta, medio, curva, ordenar } from "./diagrama.js";

const { createApp } = Vue;

createApp({
  data() {
    return {
      tamano: 100,
      vista: "arquitectura",
      pestanas: [
        { id: "arquitectura", titulo: "Arquitectura" },
        { id: "servicios", titulo: "Servicios" },
        { id: "datos", titulo: "Datos" },
      ],

      nodos: [],
      aristas: [],
      lienzo: { w: 1200, h: 640 },
      equipo: "",
      demo: false,
      motivo: "",

      modo: "normal",
      modos: [
        { id: "normal", titulo: "Qué pasa" },
        { id: "permisos", titulo: "Qué lo autoriza" },
        { id: "dependencias", titulo: "Qué se rompe" },
      ],
      roto: null,
      ramasVivas: [],
      ultimaFila: null,
      cuandoLlego: null,
      ahora: Date.now(),
      _apagar: null,

      detalle: null,
      pestanaDetalle: "Qué es",
      yaml: [],

      estado: { nodos: {} },

      consulta: { accion: "ultimas", n: 50, umbral: 90 },
      pidiendo: false,
      respuesta: null,
    };
  },

  computed: {
    // Las flechas con su camino ya calculado.
    aristasDibujo() {
      const por = {};
      this.nodos.forEach((n) => (por[n.id] = n));
      return this.aristas
        .filter((a) => por[a.de] && por[a.a])
        .map((a, i) => ({
          ...a,
          d: ruta(por[a.de], por[a.a], i),
          m: medio(por[a.de], por[a.a]),
        }));
    },

    // Lo que le pasa a cada caja si quitamos la que está seleccionada.
    efectos() {
      const n = this.nodoPorId(this.roto);
      if (!n || !n.si_falta) return {};
      const m = {};
      n.si_falta.forEach((f) => { m[f.nodo] = f; });
      return m;
    },

    filas() {
      if (!this.respuesta) return [];
      return ordenar(this.respuesta.filas || []);
    },

    resumen() {
      return this.respuesta && this.respuesta.resumen;
    },

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

    // Cuánto hace del último mensaje, y si el equipo dejó de publicar.
    // Importa en clase: un alumno con el dispositivo apagado tiene que
    // leer "no está publicando", no quedarse mirando un dibujo quieto.
    antiguedad() {
      if (!this.cuandoLlego) return null;
      const s = Math.max(0, Math.round((this.ahora - this.cuandoLlego) / 1000));
      if (s < 60) return `hace ${s} s`;
      if (s < 3600) return `hace ${Math.round(s / 60)} min`;
      return `hace ${Math.round(s / 3600)} h`;
    },

    parado() {
      return this.cuandoLlego !== null && this.ahora - this.cuandoLlego > 60000;
    },

    yUmbral() {
      const g = this.grafico;
      if (!g || !this.resumen) return null;
      const u = Number(this.resumen.umbral);
      return u < g.min || u > g.max ? null : g.enY(u);
    },
  },

  async mounted() {
    const a = await (await fetch("/api/arquitectura")).json();
    this.nodos = a.nodos;
    this.aristas = a.aristas;
    this.lienzo = a.lienzo;
    this.equipo = a.equipo;
    this.demo = a.demo;
    this.motivo = a.motivo;

    this.escuchar();
    // Cada cinco segundos, no cada uno: «hace 40 s» no necesita más
    // precisión, y tocar una propiedad reactiva repinta el dibujo
    // entero. A un segundo, la página no para quieta nunca.
    setInterval(() => { this.ahora = Date.now(); }, 5000);
    this.pedirEstado();
    setInterval(() => this.pedirEstado(), 30000);
    this.pedirDatos();
  },

  methods: {
    ajustar(d) {
      this.tamano = Math.min(170, Math.max(70, this.tamano + d));
      document.getElementById("app").style.zoom = this.tamano / 100;
    },

    // Cada mensaje que llega enciende sus ramas durante un momento. El
    // parpadeo es el dato: si una rama no se enciende, su regla no la
    // activó.
    escuchar() {
      const es = new EventSource("/api/eventos");
      es.onmessage = (ev) => {
        const d = JSON.parse(ev.data);
        if (d.tipo !== "fila") return;
        this.ultimaFila = d.fila;
        this.cuandoLlego = Date.parse(d.fila.momento) || Date.now();
        // Un evento histórico no enciende nada: no acaba de pasar.
        if (d.historico) return;
        this.ramasVivas = d.ramas;
        clearTimeout(this._apagar);
        this._apagar = setTimeout(() => { this.ramasVivas = []; }, 1600);
      };
    },

    async pedirEstado() {
      if (this.demo) return;
      try {
        this.estado = await (await fetch("/api/estado")).json();
      } catch (e) { /* la vista aguanta sin estado */ }
    },

    nodoPorId(id) {
      return this.nodos.find((n) => n.id === id) || null;
    },

    // En el modo de dependencias el clic quita la caja en vez de abrir
    // su ficha: en un proyector, pasar el ratón no se ve.
    clicNodo(n) {
      if (this.modo === "dependencias") {
        this.roto = this.roto === n.id ? null : n.id;
        return;
      }
      this.abrir(n);
    },

    // Una flecha muere si toca la caja que quitamos, o si sale de algo
    // que ha dejado de funcionar.
    aristaMuerta(a) {
      if (!this.roto) return false;
      if (a.de === this.roto || a.a === this.roto) return true;
      const e = this.efectos[a.de];
      return !!(e && e.grave);
    },

    async abrir(n) {
      this.detalle = n;
      this.pestanaDetalle = "Qué es";
      this.yaml = [];
      const r = await (await fetch("/api/yaml?nodo=" + encodeURIComponent(n.id))).json();
      this.yaml = r.bloques || [];
    },

    // Resaltado mínimo del YAML. No es un analizador: pinta lo justo
    // para leerlo de un vistazo en un proyector.
    pintar(texto) {
      const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      return texto.split("\n").map((l) => {
        const e = esc(l);
        if (/^\s*#/.test(e)) return `<span class="c">${e}</span>`;
        return e
          .replace(/(![A-Za-z]+)/g, '<span class="f">$1</span>')
          .replace(/^(\s*)([A-Za-z0-9_-]+):/, '$1<span class="k">$2</span>:');
      }).join("\n");
    },

    async pedirDatos() {
      this.pidiendo = true;
      try {
        const p = new URLSearchParams({
          accion: this.consulta.accion,
          n: this.consulta.n,
          umbral: this.consulta.umbral,
        });
        this.respuesta = await (await fetch("/api/datos?" + p)).json();
      } catch (e) {
        this.respuesta = { error: String(e), filas: [] };
      } finally {
        this.pidiendo = false;
      }
    },

    hora(iso) {
      const d = new Date(iso);
      return isNaN(d) ? iso : d.toLocaleTimeString();
    },
  },
}).mount("#app");
