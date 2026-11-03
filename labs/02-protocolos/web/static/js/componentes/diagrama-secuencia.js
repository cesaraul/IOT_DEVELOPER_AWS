/* Diagrama de secuencia animado.
 *
 * Recibe un guión (actores + pasos) y lo reproduce mensaje a mensaje: cada
 * flecha se dibuja sola, un punto viaja por ella y el panel lateral explica
 * qué acaba de pasar mientras el contador de bytes se va sumando.
 *
 * Se usa igual para HTTP y para MQTT, y servirá para cualquier otro protocolo
 * que necesitemos explicar más adelante.
 */

window.Componentes = window.Componentes || {};

/* La geometría va en unidades del viewBox, no en píxeles: el SVG se escala al
 * ancho disponible, así que lo que importa es el tamaño de la letra RELATIVO
 * al ancho del lienzo. Por eso el lienzo se ensancha cuando hay más actores,
 * en vez de apretar los mensajes. */
const MARGEN_X = 110;
const Y_INICIO = 112;
const ALTO_PASO = 82;

window.Componentes.DiagramaSecuencia = {
  props: {
    guion: { type: Object, required: true },
  },

  data() {
    return { indice: -1, reproduciendo: false, velocidad: 1 };
  },

  computed: {
    actores() { return this.guion.actores; },
    pasos() { return this.guion.pasos; },
    visibles() { return this.pasos.slice(0, this.indice + 1); },
    pasoActual() { return this.indice >= 0 ? this.pasos[this.indice] : null; },
    terminado() { return this.indice >= this.pasos.length - 1; },
    alto() { return Y_INICIO + this.pasos.length * ALTO_PASO + 34; },
    /** Más actores, lienzo más ancho: así las etiquetas no se pisan. */
    ancho() { return 760 + Math.max(0, this.actores.length - 2) * 220; },
    span() { return this.ancho - 2 * MARGEN_X; },
    /** El lienzo se ensancha con cada actor, así que la letra crece con él:
     *  de otro modo un escenario de 4 actores se leería a la mitad de tamaño
     *  que uno de 2. Las clases del SVG usan "em" sobre este valor. */
    tamanoTexto() { return (20 * this.ancho) / 760; },

    bytesAcumulados() {
      return this.visibles.reduce((suma, p) => suma + (p.bytes || 0), 0);
    },
    utilesAcumulados() {
      return this.visibles.reduce((suma, p) => suma + (p.utiles || 0), 0);
    },
    eficiencia() {
      return this.bytesAcumulados ? (100 * this.utilesAcumulados) / this.bytesAcumulados : 0;
    },
    bytesTotales() {
      return this.pasos.reduce((suma, p) => suma + (p.bytes || 0), 0);
    },
  },

  watch: {
    guion() {
      this.reiniciar();
      this.$nextTick(() => this.reproducir());
    },
  },

  mounted() {
    this.reproducir();
  },

  unmounted() {
    clearTimeout(this.temporizador);
  },

  methods: {
    x(i) {
      const n = this.actores.length;
      return n > 1 ? MARGEN_X + (i * this.span) / (n - 1) : MARGEN_X + this.span / 2;
    },
    y(n) {
      return Y_INICIO + n * ALTO_PASO;
    },
    /** Punto final de la flecha: si el mensaje se pierde, muere a mitad. */
    xFin(p) {
      const origen = this.x(p.de);
      const destino = this.x(p.a);
      return p.perdido ? origen + (destino - origen) * 0.55 : destino;
    },
    esPropio(p) {
      return p.de === p.a;
    },
    caminoPropio(p, n) {
      const x0 = this.x(p.de);
      const y0 = this.y(n);
      return `M ${x0} ${y0 - 14} C ${x0 + 92} ${y0 - 18}, ${x0 + 92} ${y0 + 26}, ${x0 + 5} ${y0 + 21}`;
    },

    siguiente() {
      if (this.terminado) return;
      this.indice += 1;
      this.animar(this.indice);
    },
    anterior() {
      this.pausar();
      if (this.indice >= 0) this.indice -= 1;
    },
    reiniciar() {
      this.pausar();
      this.indice = -1;
    },
    pausar() {
      this.reproduciendo = false;
      clearTimeout(this.temporizador);
    },
    alternar() {
      if (this.reproduciendo) return this.pausar();
      if (this.terminado) this.indice = -1;
      this.reproducir();
    },
    reproducir() {
      this.reproduciendo = true;
      this.avanzarSolo();
    },
    avanzarSolo() {
      if (!this.reproduciendo) return;
      if (this.terminado) {
        this.reproduciendo = false;
        return;
      }
      this.siguiente();
      this.temporizador = setTimeout(() => this.avanzarSolo(), 1600 / this.velocidad);
    },

    /** La animación propiamente dicha: GSAP sobre el SVG recién renderizado. */
    animar(n) {
      this.$nextTick(() => {
        const svg = this.$refs.lienzo;
        if (!svg) return;
        const grupo = svg.querySelector(`[data-paso="${n}"]`);
        if (!grupo) return;

        const paso = this.pasos[n];
        const duracion = 0.75 / this.velocidad;
        const trazo = grupo.querySelector(".trazo");
        const punto = grupo.querySelector(".punto");
        const textos = grupo.querySelectorAll("text");

        if (trazo) {
          const largo = trazo.getTotalLength ? trazo.getTotalLength() : 600;
          gsap.fromTo(
            trazo,
            { strokeDasharray: largo, strokeDashoffset: largo },
            { strokeDashoffset: 0, duration: duracion, ease: "power2.out" }
          );
        }
        if (punto && !this.esPropio(paso)) {
          gsap.fromTo(
            punto,
            { attr: { cx: this.x(paso.de) }, scale: 0.4, opacity: 1 },
            {
              attr: { cx: this.xFin(paso) },
              scale: 1,
              duration: duracion,
              ease: "power2.out",
              onComplete: () => gsap.to(punto, { opacity: 0, duration: 0.3, delay: 0.15 }),
            }
          );
        }
        gsap.fromTo(
          textos,
          { opacity: 0, y: -5 },
          { opacity: 1, y: 0, duration: 0.3, delay: duracion * 0.6, stagger: 0.05 }
        );

        // El actor que recibe "acusa" el golpe.
        const destino = svg.querySelector(`[data-actor="${paso.a}"]`);
        if (destino) {
          gsap.fromTo(destino, { scale: 1 }, { scale: 1.07, duration: 0.18, yoyo: true,
            repeat: 1, transformOrigin: "center", delay: duracion * 0.8 });
        }

        // Mantener a la vista el mensaje nuevo.
        const caja = this.$refs.scroll;
        if (caja) {
          const proporcion = (this.y(n) + 40) / this.alto;
          const objetivo = Math.max(0, proporcion * caja.scrollHeight - caja.clientHeight * 0.6);
          caja.scrollTo({ top: objetivo, behavior: "smooth" });
        }
      });
    },

    bytes(n) {
      return util.bytes(n);
    },
  },

  template: `
<div class="diagrama">

  <div class="diagrama-barra">
    <button class="btn btn-secundario" @click="reiniciar" title="Volver al inicio">⏮</button>
    <button class="btn btn-secundario" @click="anterior" :disabled="indice < 0">◀ Atrás</button>
    <button class="btn btn-principal" @click="alternar">
      {{ reproduciendo ? '⏸ Pausar' : (terminado ? '↻ Repetir' : '▶ Reproducir') }}
    </button>
    <button class="btn btn-secundario" @click="pausar(); siguiente()" :disabled="terminado">Paso ▶</button>
    <span class="progreso">Paso {{ Math.max(indice + 1, 0) }} de {{ pasos.length }}</span>
    <label class="velocidad">
      Velocidad
      <select v-model.number="velocidad">
        <option :value="0.5">lenta</option>
        <option :value="1">normal</option>
        <option :value="2">rápida</option>
      </select>
    </label>
  </div>

  <div class="diagrama-cuerpo">

    <div class="diagrama-lienzo" ref="scroll">
      <svg ref="lienzo" :viewBox="'0 0 ' + ancho + ' ' + alto" preserveAspectRatio="xMidYMin meet"
           :style="{ fontSize: tamanoTexto + 'px' }">
        <defs>
          <marker v-for="c in ['tcp','tls','app','error','control']" :key="c"
                  :id="'punta-' + c" markerWidth="8" markerHeight="8" refX="7" refY="4"
                  orient="auto">
            <path d="M0,0 L8,4 L0,8 z" :class="'relleno-' + c"/>
          </marker>
        </defs>

        <!-- actores y líneas de vida -->
        <g v-for="(actor, i) in actores" :key="actor">
          <g :data-actor="i">
            <rect :x="x(i) - 92" y="20" width="184" height="52" rx="10" class="caja-actor"/>
            <text :x="x(i)" y="54" text-anchor="middle" class="texto-actor">{{ actor }}</text>
          </g>
          <line :x1="x(i)" y1="74" :x2="x(i)" :y2="alto - 16" class="linea-vida"/>
        </g>

        <!-- mensajes -->
        <g v-for="(p, n) in visibles" :key="n" :data-paso="n"
           :class="['paso', p.clase, { perdido: p.perdido }]">

          <template v-if="esPropio(p)">
            <path class="trazo" :d="caminoPropio(p, n)" fill="none"
                  :marker-end="'url(#punta-' + p.clase + ')'"/>
            <text :x="x(p.de) + 106" :y="y(n) + 8" class="texto-mensaje texto-izq">{{ p.etiqueta }}</text>
          </template>

          <template v-else>
            <line class="trazo" :x1="x(p.de)" :y1="y(n)" :x2="xFin(p)" :y2="y(n)"
                  :marker-end="'url(#punta-' + p.clase + ')'"/>
            <circle class="punto" :cx="x(p.de)" :cy="y(n)" r="8"/>
            <text :x="(x(p.de) + xFin(p)) / 2" :y="y(n) - 15" text-anchor="middle"
                  class="texto-mensaje">{{ p.etiqueta }}</text>
            <text v-if="p.bytes" :x="(x(p.de) + xFin(p)) / 2" :y="y(n) + 28"
                  text-anchor="middle" class="texto-bytes">
              {{ p.bytes }} B<tspan v-if="p.utiles" class="texto-utiles"> · {{ p.utiles }} útiles</tspan>
            </text>
            <text v-if="p.perdido" :x="xFin(p) + 26" :y="y(n) + 8" class="texto-perdido">✗ perdido</text>
          </template>
        </g>
      </svg>
    </div>

    <aside class="diagrama-panel">
      <div class="contadores">
        <div>
          <span class="etiqueta">En la red hasta aquí</span>
          <strong>{{ bytes(bytesAcumulados) }}</strong>
          <small>de {{ bytes(bytesTotales) }} en total</small>
        </div>
        <div>
          <span class="etiqueta">De eso, tu dato</span>
          <strong class="verde">{{ bytes(utilesAcumulados) }}</strong>
          <small>{{ eficiencia.toFixed(1) }} % de eficiencia</small>
        </div>
      </div>

      <transition name="desvanecer" mode="out-in">
        <div v-if="pasoActual" :key="indice" class="explicacion">
          <h4><span :class="['punto-clase', pasoActual.clase]"></span>{{ pasoActual.etiqueta }}</h4>
          <p>{{ pasoActual.detalle }}</p>
          <pre v-if="pasoActual.crudo" class="crudo">{{ pasoActual.crudo }}</pre>
        </div>
        <div v-else key="inicio" class="explicacion">
          <h4>{{ guion.titulo }}</h4>
          <p>{{ guion.resumen }}</p>
        </div>
      </transition>

      <transition name="desvanecer">
        <div v-if="terminado" class="conclusion">
          <strong>Conclusión</strong>
          <p>{{ guion.conclusion }}</p>
        </div>
      </transition>
    </aside>

  </div>
</div>`,
};
