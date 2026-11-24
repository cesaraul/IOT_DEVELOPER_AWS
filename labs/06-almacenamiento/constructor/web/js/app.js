// El pegamento: recoge las decisiones, pide el YAML, pinta los avisos y
// manda el archivo al servidor para que lo escriba en tu disco.

import { construirYaml, enlaceDocs } from "./plantilla.js";
import { calcularAvisos } from "./avisos.js";

const { createApp } = Vue;

createApp({
  data() {
    return {
      tamano: 100,
      guardando: false,
      rutaGuardada: "",

      // El estado arranca con los valores correctos del laboratorio. La
      // idea no es que empiecen de cero, sino que puedan tocar y ver qué
      // se rompe — y volver atrás.
      e: {
        nombre: "demo-clase3",
        clavePart: "dispositivo",
        tipoPart: "S",
        claveOrden: "momento",
        tipoOrden: "S",
        capacidad: "aprovisionada",
        aDynamo: true,
        aS3: true,
        anadeDispositivo: true,
        anadeMomento: true,
        conWhere: false,
        condicion: "alarma = true",
        yaDesplegado: false,
      },
    };
  },

  computed: {
    yaml() {
      return construirYaml(this.e);
    },

    avisos() {
      return calcularAvisos(this.e);
    },

    // Resaltado mínimo. No es un analizador de YAML: solo pinta de colores
    // lo que ayuda a leerlo de un vistazo en un proyector.
    yamlColoreado() {
      const escapar = (t) =>
        t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

      return this.yaml
        .split("\n")
        .map((linea) => {
          const l = escapar(linea);
          if (/^\s*#/.test(l)) return `<span class="c">${l}</span>`;
          return l
            .replace(/(![A-Za-z]+)/g, '<span class="f">$1</span>')
            .replace(/^(\s*)([A-Za-z0-9_-]+):/, '$1<span class="k">$2</span>:');
        })
        .join("\n");
    },

    comando() {
      return [
        "cd labs/06-almacenamiento",
        "",
        "aws cloudformation deploy \\",
        "  --template-file mi-clase6.yaml \\",
        "  --stack-name clase6 \\",
        "  --capabilities CAPABILITY_NAMED_IAM \\",
        "  --region us-east-2 \\",
        "  --profile curso",
      ].join("\n");
    },
  },

  watch: {
    // Si cambias algo después de guardar, el mensaje de "guardada" deja de
    // ser verdad. Mejor que desaparezca a que te confunda.
    e: {
      deep: true,
      handler() {
        this.rutaGuardada = "";
      },
    },
  },

  methods: {
    docs(tipo) {
      return enlaceDocs(tipo);
    },

    ajustar(delta) {
      this.tamano = Math.min(170, Math.max(70, this.tamano + delta));
      document.getElementById("app").style.zoom = this.tamano / 100;
    },

    async guardar() {
      this.guardando = true;
      try {
        const r = await fetch("/guardar", { method: "POST", body: this.yaml });
        const datos = await r.json();
        this.rutaGuardada = datos.ruta;
      } catch (e) {
        alert("No pude guardar: " + e);
      } finally {
        this.guardando = false;
      }
    },
  },
}).mount("#app");
