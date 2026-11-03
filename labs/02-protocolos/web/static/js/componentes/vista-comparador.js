/* Comparador en vivo: los dos canales, lado a lado, con datos reales. */

window.Componentes = window.Componentes || {};

window.Componentes.VistaComparador = {
  data() {
    return { tienda };
  },

  computed: {
    http() { return this.tienda.estado.metricas.http; },
    mqtt() { return this.tienda.estado.metricas.mqtt; },
    hayDatos() { return this.http.mensajes > 0 && this.mqtt.mensajes > 0; },
    veces() {
      return this.mqtt.bytes_por_mensaje
        ? (this.http.bytes_por_mensaje / this.mqtt.bytes_por_mensaje).toFixed(1)
        : "—";
    },
    ahorro() { return (this.http.mb_por_mes - this.mqtt.mb_por_mes).toFixed(1); },
  },

  methods: {
    bytes: util.bytes,
  },

  template: `
<section class="vista">
  <header class="vista-cabecera">
    <h2>Comparador en vivo</h2>
    <p class="intro">
      Los dos canales envían <strong>exactamente el mismo dato</strong>, leído del mismo
      sensor simulado. Lo único que cambia es el protocolo.
    </p>
  </header>

  <div class="rejilla-2">
    <article class="tarjeta tarjeta-http">
      <h2>HTTP <span class="etiqueta">POST /telemetry</span></h2>
      <div class="numeron">{{ http.mb_por_mes }} <small>MB/mes</small></div>
      <dl class="datos">
        <div><dt>Mensajes</dt><dd>{{ http.mensajes }}</dd></div>
        <div><dt>Bytes por mensaje</dt><dd>{{ http.bytes_por_mensaje }} B</dd></div>
        <div><dt>Transmitido</dt><dd>{{ bytes(http.bytes_total) }}</dd></div>
        <div><dt>Dato útil</dt><dd>{{ bytes(http.bytes_utiles) }}</dd></div>
        <div><dt>Errores</dt><dd>{{ http.errores }}</dd></div>
        <div><dt>Reintentos</dt><dd>{{ http.reintentos }}</dd></div>
        <div><dt>Polling GET /config</dt><dd>{{ http.polls }}</dd></div>
        <div><dt>Bytes de polling</dt><dd>{{ bytes(http.bytes_polling) }}</dd></div>
      </dl>
      <div class="eficiencia">
        <div class="barra-ef"><span :style="{ width: http.eficiencia + '%' }"></span></div>
        <strong>{{ http.eficiencia }} %</strong> de eficiencia
      </div>
    </article>

    <article class="tarjeta tarjeta-mqtt">
      <h2>MQTT <span class="etiqueta">{{ tienda.estado.base_topic }}/telemetria</span></h2>
      <div class="numeron">{{ mqtt.mb_por_mes }} <small>MB/mes</small></div>
      <dl class="datos">
        <div><dt>Mensajes</dt><dd>{{ mqtt.mensajes }}</dd></div>
        <div><dt>Bytes por mensaje</dt><dd>{{ mqtt.bytes_por_mensaje }} B</dd></div>
        <div><dt>Transmitido</dt><dd>{{ bytes(mqtt.bytes_total) }}</dd></div>
        <div><dt>Dato útil</dt><dd>{{ bytes(mqtt.bytes_utiles) }}</dd></div>
        <div><dt>Errores</dt><dd>{{ mqtt.errores }}</dd></div>
        <div><dt>Reintentos</dt><dd>{{ mqtt.reintentos }}</dd></div>
      </dl>
      <div class="eficiencia">
        <div class="barra-ef"><span :style="{ width: mqtt.eficiencia + '%' }"></span></div>
        <strong>{{ mqtt.eficiencia }} %</strong> de eficiencia
      </div>
    </article>
  </div>

  <div class="veredicto">
    <template v-if="hayDatos">
      Con este mismo dato, <strong>HTTP transmite {{ veces }}× más bytes por mensaje</strong>
      que MQTT ({{ http.bytes_por_mensaje }} B frente a {{ mqtt.bytes_por_mensaje }} B).
      Proyectado a un mes por dispositivo: <strong>{{ ahorro }} MB de diferencia</strong>.
      Multiplícalo por el tamaño de tu flota.
    </template>
    <template v-else>Esperando las primeras muestras de los dos canales…</template>
  </div>

  <p class="nota">
    El polling se cuenta aparte a propósito: no lleva datos, pero cuesta. Preguntar
    «¿hay novedades?» son {{ bytes(http.bytes_polling) }} con 0 % de dato útil.
  </p>
</section>`,
};
