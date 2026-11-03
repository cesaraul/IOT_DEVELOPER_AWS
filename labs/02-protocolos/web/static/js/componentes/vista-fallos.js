/* Laboratorio de fallos: romper el sistema a propósito. */

window.Componentes = window.Componentes || {};

window.Componentes.VistaFallos = {
  data() {
    return { tienda, p503: 0, p429: 0, latencia: 0, redCaida: false };
  },

  watch: {
    // Si otro navegador mueve los interruptores, estos se ponen al día.
    "tienda.estado.fallos.red_caida"(valor) {
      this.redCaida = valor;
    },
  },

  mounted() {
    const f = this.tienda.estado.fallos;
    this.p503 = Math.round(f.tasa_503 * 100);
    this.p429 = Math.round(f.tasa_429 * 100);
    this.latencia = f.latencia_ms;
    this.redCaida = f.red_caida;
  },

  methods: {
    aplicar() {
      util.enviar("/api/fallos", {
        tasa_503: this.p503 / 100,
        tasa_429: this.p429 / 100,
        latencia_ms: this.latencia,
      });
    },
    cortar() {
      util.enviar("/api/fallos", { red_caida: this.redCaida });
    },
  },

  template: `
<section class="vista">
  <header class="vista-cabecera">
    <h2>Laboratorio de fallos</h2>
    <p class="intro">
      Rompe el sistema a propósito y observa cómo responde cada protocolo. El
      dispositivo tiene cola local y backoff exponencial: míralos actuar en la bitácora.
    </p>
  </header>

  <div class="rejilla-2">
    <div class="tarjeta">
      <h3>Interruptores</h3>
      <label class="control-rango">Respuestas <code>503</code>
        <input type="range" min="0" max="100" step="10" v-model.number="p503" @change="aplicar">
        <output>{{ p503 }} %</output>
      </label>
      <label class="control-rango">Respuestas <code>429</code>
        <input type="range" min="0" max="100" step="10" v-model.number="p429" @change="aplicar">
        <output>{{ p429 }} %</output>
      </label>
      <label class="control-rango">Latencia del servidor
        <input type="range" min="0" max="3000" step="100" v-model.number="latencia" @change="aplicar">
        <output>{{ latencia }} ms</output>
      </label>
      <label class="interruptor">
        <input type="checkbox" v-model="redCaida" @change="cortar">
        <span>Cortar la red del dispositivo
          <small>dispara el testamento MQTT y llena la cola local de HTTP</small>
        </span>
      </label>
    </div>

    <div class="tarjeta">
      <h3>Estado del dispositivo <small>topic <code>…/estado</code></small></h3>
      <div class="numeron" :class="tienda.estadoDispositivo === 'online' ? 'verde' : 'rojo'">
        {{ tienda.estadoDispositivo }}
      </div>
      <p class="nota">
        Lo publica el propio dispositivo al conectarse, con <code>retain</code>. Si la
        conexión muere sin despedida, lo publica el <strong>broker</strong> en su nombre,
        pasado 1.5 veces el keepalive.
      </p>
      <dl class="datos">
        <div><dt>Errores HTTP</dt><dd>{{ tienda.estado.metricas.http.errores }}</dd></div>
        <div><dt>Reintentos</dt><dd>{{ tienda.estado.metricas.http.reintentos }}</dd></div>
      </dl>
    </div>
  </div>

  <h3>Bitácora</h3>
  <div class="consola consola-alta">
    <div v-for="a in tienda.avisos" :key="a.clave" :class="a.nivel">
      {{ a.hora }}  {{ a.texto }}
    </div>
  </div>
</section>`,
};
