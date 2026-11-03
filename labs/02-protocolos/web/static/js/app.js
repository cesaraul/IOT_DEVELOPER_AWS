/* Arranque de la interfaz: menú, registro de componentes y conexiones. */

const MENU = [
  {
    titulo: "Fundamentos",
    nota: "Cada protocolo por separado, explicado etapa por etapa.",
    items: [
      { id: "http-pasos", icono: "①", titulo: "HTTP paso a paso",
        resumen: "Del saludo TCP a la respuesta" },
      { id: "mqtt-pasos", icono: "②", titulo: "MQTT paso a paso",
        resumen: "Del CONNECT al testamento" },
    ],
  },
  {
    titulo: "Laboratorio en vivo",
    nota: "Tráfico real contra un broker y un servidor de verdad.",
    items: [
      { id: "comparador", icono: "⚖", titulo: "Comparador", resumen: "Los dos, lado a lado" },
      { id: "inspector", icono: "🔍", titulo: "Inspector", resumen: "Paquetes byte a byte" },
      { id: "comandos", icono: "⏱", titulo: "Comandos", resumen: "Latencia de una orden" },
      { id: "topics", icono: "🌳", titulo: "Topics", resumen: "Comodines + y #" },
      { id: "fallos", icono: "⚡", titulo: "Fallos", resumen: "Rompe el sistema" },
      { id: "qos", icono: "📬", titulo: "QoS y retención", resumen: "Qué sobrevive y qué no" },
    ],
  },
];

/** El tamaño elegido se recuerda en este navegador; si no se puede guardar
 *  (ventana privada, almacenamiento bloqueado), la interfaz funciona igual. */
function tamanoGuardado() {
  try {
    return Number(localStorage.getItem("lab-tamano")) || 100;
  } catch (error) {
    return 100;
  }
}

const aplicacion = Vue.createApp({
  data() {
    return { tienda, menu: MENU, tamano: tamanoGuardado() };
  },

  mounted() {
    this.aplicarTamano();
  },

  computed: {
    vista: {
      get() { return this.tienda.vista; },
      set(valor) { this.tienda.vista = valor; },
    },
    itemActual() {
      for (const grupo of this.menu) {
        const encontrado = grupo.items.find((i) => i.id === this.vista);
        if (encontrado) return encontrado;
      }
      return null;
    },
    subtitulo() {
      return this.itemActual
        ? `${this.itemActual.titulo} — ${this.itemActual.resumen}`
        : "El mismo sensor hablando por HTTP y por MQTT";
    },
    textoConexion() { return this.tienda.conexion; },
    claseConexion() {
      return this.tienda.conexion === "en vivo" ? "pastilla-ok" : "pastilla-mal";
    },
  },

  methods: {
    reiniciarContadores() {
      util.enviar("/api/reset");
    },
    ajustarTamano(delta) {
      this.tamano = Math.min(200, Math.max(70, this.tamano + delta));
      this.aplicarTamano();
      try {
        localStorage.setItem("lab-tamano", this.tamano);
      } catch (error) {
        /* sin almacenamiento: el tamaño simplemente no se recuerda */
      }
    },
    aplicarTamano() {
      document.body.style.zoom = this.tamano / 100;
    },
  },
});

// Registro de componentes: el nombre en kebab-case es el que usa la plantilla.
aplicacion.component("diagrama-secuencia", window.Componentes.DiagramaSecuencia);
aplicacion.component("vista-http-pasos", window.Componentes.VistaHttpPasos);
aplicacion.component("vista-mqtt-pasos", window.Componentes.VistaMqttPasos);
aplicacion.component("vista-comparador", window.Componentes.VistaComparador);
aplicacion.component("vista-inspector", window.Componentes.VistaInspector);
aplicacion.component("vista-comandos", window.Componentes.VistaComandos);
aplicacion.component("vista-topics", window.Componentes.VistaTopics);
aplicacion.component("vista-fallos", window.Componentes.VistaFallos);
aplicacion.component("vista-qos", window.Componentes.VistaQos);

aplicacion.mount("#app");

conectarEventos();
refrescarEstado();
setInterval(refrescarEstado, 1000);
