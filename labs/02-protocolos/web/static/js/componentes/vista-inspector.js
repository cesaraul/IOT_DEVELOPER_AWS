/* Inspector de paquetes: el tráfico real, byte a byte. */

window.Componentes = window.Componentes || {};

window.Componentes.VistaInspector = {
  data() {
    return { tienda };
  },

  computed: {
    lista() {
      if (this.tienda.filtro === "todos") return this.tienda.paquetes;
      return this.tienda.paquetes.filter((p) => p.protocolo === this.tienda.filtro);
    },
  },

  methods: {
    titulo(p) {
      return p.protocolo === "http"
        ? `${p.ruta} → ${p.codigo}`
        : `${p.topic} · QoS ${p.qos}${p.retenido ? " · retenido" : ""}`;
    },
    eficiencia(p) {
      return p.bytes_total ? Math.round((100 * p.bytes_utiles) / p.bytes_total) : 0;
    },
    alternar(p) {
      p.abierto = !p.abierto;
      // Si no se pausa, los mensajes nuevos empujan hacia abajo justo lo que lees.
      if (p.abierto) this.tienda.pausa = true;
    },
  },

  template: `
<section class="vista">
  <header class="vista-cabecera">
    <h2>Inspector de paquetes</h2>
    <p class="intro">
      Cada mensaje que pasa de verdad por la red.
      <span class="chip chip-overhead">rojo</span> es protocolo,
      <span class="chip chip-topic">naranja</span> el nombre del topic y
      <span class="chip chip-util">verde</span> tu dato.
      Haz clic para desplegar: la lista se pausa sola mientras lees.
    </p>
  </header>

  <div class="controles">
    <label><input type="radio" value="todos" v-model="tienda.filtro"> Todos</label>
    <label><input type="radio" value="http" v-model="tienda.filtro"> Solo HTTP</label>
    <label><input type="radio" value="mqtt" v-model="tienda.filtro"> Solo MQTT</label>
    <label class="derecha"><input type="checkbox" v-model="tienda.pausa"> Pausar</label>
  </div>

  <transition-group tag="div" class="lista-paquetes" name="paquete">
    <article v-for="p in lista" :key="p.clave"
             :class="['paquete', p.protocolo, { error: p.codigo >= 400, abierto: p.abierto }]">
      <div class="paquete-cabeza" @click="alternar(p)">
        <b :class="'texto-' + p.protocolo">{{ p.protocolo }}</b>
        <span class="crece">{{ titulo(p) }}</span>
        <span>{{ p.bytes_total }} B · <strong>{{ eficiencia(p) }}% útil</strong></span>
      </div>
      <div class="paquete-cuerpo" v-if="p.abierto">
        <pre class="crudo">{{ p.texto }}</pre>
        <div class="desglose">
          <span v-for="parte in p.partes" :key="parte.etiqueta"
                :class="parte.clase" :style="{ flex: Math.max(parte.bytes, 1) }"
                :title="parte.etiqueta + ': ' + parte.bytes + ' B'">{{ parte.bytes }}</span>
        </div>
        <div class="leyenda">
          <span v-for="parte in p.partes" :key="parte.etiqueta">
            {{ parte.etiqueta }}: {{ parte.bytes }} B
          </span>
        </div>
      </div>
    </article>
  </transition-group>

  <p v-if="!lista.length" class="nota">Esperando tráfico…</p>
</section>`,
};
