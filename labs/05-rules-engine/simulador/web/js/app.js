// El simulador, pegado con Vue.
//
// Todo corre en TU navegador: el motor de reglas, las funciones y la
// animación. Lo único que hay fuera es el broker (para recibir los mensajes
// del dispositivo) y el propio dispositivo. Por eso no hay servidor que
// mantener ni API que llamar.

import { evaluar, escribirSQL } from "./motor.js";
import { FUNCIONES, buscarFuncion } from "./funciones.js";

const { createApp } = Vue;

// Los topics donde escribimos nosotros. Hay que ignorarlos al recibir, o la
// regla se alimenta de su propia salida y entra en bucle.
//
// No es una manía del simulador: en AWS pasa exactamente igual. Una regla
// con FROM 'fablab/#' que republica dentro de 'fablab/...' se dispara con
// su propio mensaje, para siempre, y la factura la pagas tú. Es uno de los
// errores caros clásicos del Rules Engine.
const TOPICS_SALIDA = ["fablab/alarmas", "fablab/revisados"];

createApp({
  data() {
    return {
      tamano: 100,
      conectado: false,
      cliente: null,

      regla: {
        desde: "fablab/planta1/+/telemetria",
        condicion: { campo: "alarma", operador: "=", valor: true },
        seleccion: {
          todo: false,
          campos: ["nivel", "temp"],
          anadeDispositivo: false,
          anadeHora: false,
        },
        accion: { tipo: "republicar", topic: "fablab/alarmas", funcion: "avisa_una_vez" },
      },

      camposPosibles: ["nivel", "temp", "alarma"],
      funciones: FUNCIONES,
      estadosLambda: {},

      cont: { recibidos: 0, aceptados: 0, descartados: 0, correos: 0 },
      historial: [],
      correos: [],
      tabla: [],
      registroLambda: [],

      estadoEquipo: { bomba: "encendida", umbral: 90 },
      ultimoNivel: 60,
      destelloRegla: "",
      siguienteId: 1,
    };
  },

  computed: {
    sql() {
      return escribirSQL(this.regla);
    },

    sqlConColores() {
      // Resaltado mínimo: solo las tres palabras que estructuran la consulta.
      return this.sql.replace(
        /\b(SELECT|FROM|WHERE|AS)\b/g,
        '<span class="k">$1</span>'
      );
    },

    funcionElegida() {
      return buscarFuncion(this.regla.accion.funcion);
    },

    nombreDestino() {
      if (this.regla.accion.tipo === "republicar") return "Otro topic";
      if (this.regla.accion.tipo === "correo") return "Correo";
      return "Lambda";
    },

    subDestino() {
      if (this.regla.accion.tipo === "republicar") return this.regla.accion.topic;
      if (this.regla.accion.tipo === "correo") return "aviso por cada mensaje";
      return this.funcionElegida ? this.funcionElegida.nombre : "";
    },

    columnasTabla() {
      if (!this.tabla.length) return [];
      return Object.keys(this.tabla[0]);
    },
  },

  watch: {
    // Al cambiar de función, su memoria empieza de cero. Si no, la segunda
    // Lambda heredaría el "ya avisé" de la primera y parecería rota.
    "regla.accion.funcion"() {
      this.registroLambda = [];
      this.estadosLambda = {};
    },
  },

  methods: {
    ajustarTamano(delta) {
      this.tamano = Math.min(170, Math.max(70, this.tamano + delta));
      document.getElementById("app").style.zoom = this.tamano / 100;
    },

    alternarCampo(campo) {
      const i = this.regla.seleccion.campos.indexOf(campo);
      if (i === -1) this.regla.seleccion.campos.push(campo);
      else this.regla.seleccion.campos.splice(i, 1);
    },

    reiniciar() {
      this.cont = { recibidos: 0, aceptados: 0, descartados: 0, correos: 0 };
      this.historial = [];
      this.correos = [];
      this.tabla = [];
      this.registroLambda = [];
      this.estadosLambda = {};
      if (this.cliente) {
        this.cliente.publish("simulador/control", JSON.stringify({ reiniciar: true }));
      }
    },

    // --- el contexto que reciben las funciones -----------------------------
    contextoLambda(dispositivo) {
      return {
        dispositivo,
        avisar: (texto) => {
          this.correos.unshift(texto);
          this.correos = this.correos.slice(0, 40);
          this.cont.correos++;
        },
        guardar: (fila) => {
          this.tabla.unshift(fila);
          this.tabla = this.tabla.slice(0, 12);
        },
        escribirShadow: (deseado) => {
          this.cliente.publish("simulador/shadow/desired", JSON.stringify(deseado));
        },
        log: (linea) => {
          const hora = new Date().toLocaleTimeString("es-PE", { hour12: false });
          this.registroLambda.unshift(`${hora}  ${linea}`);
          this.registroLambda = this.registroLambda.slice(0, 30);
        },
      };
    },

    ejecutarAccion(salida, topic) {
      const accion = this.regla.accion;

      if (accion.tipo === "republicar") {
        this.cliente.publish(accion.topic, JSON.stringify(salida));
        return;
      }

      if (accion.tipo === "correo") {
        // La regla no recuerda nada: manda uno por CADA mensaje que encaja.
        // Ese contador subiendo es el bloque 6 de la clase, en vivo.
        this.correos.unshift(`Alarma en ${topic.split("/")[2]}: ${JSON.stringify(salida)}`);
        this.correos = this.correos.slice(0, 40);
        this.cont.correos++;
        return;
      }

      const funcion = this.funcionElegida;
      if (!funcion) return;

      if (!this.estadosLambda[funcion.id]) {
        this.estadosLambda[funcion.id] = funcion.estadoInicial();
      }

      funcion.ejecutar(
        salida,
        this.estadosLambda[funcion.id],
        this.contextoLambda(topic.split("/")[2] || "")
      );
    },

    procesar(topic, datos) {
      this.cont.recibidos++;

      if (typeof datos.nivel === "number") this.ultimoNivel = datos.nivel;

      const veredicto = evaluar(this.regla, topic, datos);
      this.animarPunto(veredicto.encaja, datos.alarma === true);

      if (!veredicto.encaja) {
        this.cont.descartados++;
        this.historial.unshift({
          id: this.siguienteId++,
          encaja: false,
          entrada: JSON.stringify(datos),
          motivo: veredicto.motivo,
        });
      } else {
        this.cont.aceptados++;
        this.historial.unshift({
          id: this.siguienteId++,
          encaja: true,
          salida: JSON.stringify(veredicto.resultado),
        });
        this.ejecutarAccion(veredicto.resultado, topic);
      }

      this.historial = this.historial.slice(0, 40);
    },

    // --- la animación del diagrama -----------------------------------------
    animarPunto(encaja, esAlarma) {
      const lienzo = this.$refs.lienzo;
      if (!lienzo) return;

      const punto = document.createElement("div");
      punto.className = "punto" + (esAlarma ? " alarma" : "");
      punto.style.left = "21%";
      lienzo.appendChild(punto);

      // Un frame de margen para que el navegador registre la posición
      // inicial; si no, no hay transición: salta.
      requestAnimationFrame(() => {
        punto.style.left = "30%";
      });

      const quitar = () => {
        punto.style.opacity = "0";
        setTimeout(() => punto.remove(), 400);
      };

      setTimeout(() => {
        this.destelloRegla = encaja ? "acierta" : "falla";
        setTimeout(() => { this.destelloRegla = ""; }, 700);

        if (encaja) {
          punto.style.left = "79%";
          setTimeout(quitar, 760);
        } else {
          quitar();
        }
      }, 740);
    },

    conectar() {
      // El navegador habla MQTT sobre WebSockets, por el puerto 9001 del
      // mismo Mosquitto al que publica el dispositivo. Es el mismo broker y
      // el mismo protocolo: solo cambia el transporte.
      const url = `ws://${location.hostname}:9001`;
      const cliente = mqtt.connect(url, { reconnectPeriod: 2000 });
      this.cliente = cliente;

      cliente.on("connect", () => {
        this.conectado = true;
        cliente.subscribe("fablab/#");
        cliente.subscribe("simulador/estado");
      });

      cliente.on("close", () => { this.conectado = false; });

      cliente.on("message", (topic, carga) => {
        let datos;
        try {
          datos = JSON.parse(carga.toString());
        } catch (e) {
          return;
        }

        if (topic === "simulador/estado") {
          this.estadoEquipo = datos;
          return;
        }

        if (TOPICS_SALIDA.includes(topic)) return;

        this.procesar(topic, datos);
      });
    },
  },

  mounted() {
    this.conectar();
  },
}).mount("#app");
