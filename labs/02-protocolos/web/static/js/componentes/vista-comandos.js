/* Comandos y latencia: la nube intentando hablarle al dispositivo. */

window.Componentes = window.Componentes || {};

window.Componentes.VistaComandos = {
  data() {
    return { tienda, intervalo: 2 };
  },

  methods: {
    async enviar(via) {
      this.tienda.cronometros[via] = "0.0 s";
      arrancarCronometro(via);
      await util.enviar("/api/comando", { via, intervalo: Number(this.intervalo) });
    },
  },

  template: `
<section class="vista">
  <header class="vista-cabecera">
    <h2>Comandos y latencia</h2>
    <p class="intro">
      Manda la misma orden por las dos vías y cronométralas. Por HTTP el dispositivo se
      entera <strong>cuando le toque preguntar</strong> (cada 15 s en este laboratorio);
      por MQTT el broker se la empuja al instante.
    </p>
  </header>

  <div class="controles">
    <label>Nuevo intervalo de muestreo
      <input type="number" v-model.number="intervalo" min="1" max="60" step="1"> s
    </label>
    <button class="btn btn-http" @click="enviar('http')">Enviar por HTTP</button>
    <button class="btn btn-mqtt" @click="enviar('mqtt')">Enviar por MQTT</button>
  </div>

  <div class="rejilla-2">
    <div class="crono crono-http">
      <span class="etiqueta">HTTP · esperando al próximo GET /config</span>
      <div class="numeron">{{ tienda.cronometros.http }}</div>
    </div>
    <div class="crono crono-mqtt">
      <span class="etiqueta">MQTT · empujado por el broker</span>
      <div class="numeron">{{ tienda.cronometros.mqtt }}</div>
    </div>
  </div>

  <table class="tabla">
    <thead>
      <tr><th>Hora</th><th>Vía</th><th>Intervalo pedido</th><th>Latencia</th></tr>
    </thead>
    <tbody>
      <tr v-for="(l, i) in tienda.latencias" :key="l.cmd_id + i">
        <td>{{ l.hora }}</td>
        <td><strong :class="'texto-' + l.via">{{ l.via.toUpperCase() }}</strong></td>
        <td>{{ l.intervalo }} s</td>
        <td><strong>{{ (l.latencia_ms / 1000).toFixed(2) }} s</strong></td>
      </tr>
      <tr v-if="!tienda.latencias.length">
        <td colspan="4" class="nota">Todavía no has enviado ningún comando.</td>
      </tr>
    </tbody>
  </table>
</section>`,
};
