/* Explorador de topics: el navegador suscrito al broker de verdad. */

window.Componentes = window.Componentes || {};

window.Componentes.VistaTopics = {
  data() {
    return {
      tienda,
      patron: "fablab/+/+/telemetria",
      conectado: false,
      recibidos: [],
      cliente: null,
      suscripcion: null,
    };
  },

  computed: {
    topics() {
      return Object.keys(this.tienda.estado.topics).sort();
    },
  },

  mounted() {
    this.cliente = mqtt.connect(`ws://${location.hostname}:9001`, {
      clientId: `navegador-${Date.now()}`,
      clean: true,
    });
    this.cliente.on("connect", () => {
      this.conectado = true;
      this.suscribir();
    });
    this.cliente.on("close", () => (this.conectado = false));
    this.cliente.on("message", (topic, carga) => {
      this.recibidos.unshift({
        hora: util.hora(),
        topic,
        carga: carga.toString().slice(0, 90),
        clave: Math.random(),
      });
      if (this.recibidos.length > 100) this.recibidos.pop();
    });
  },

  unmounted() {
    if (this.cliente) this.cliente.end(true);
  },

  methods: {
    coincide(topic) {
      return this.patron && util.coincideTopic(this.patron, topic);
    },
    suscribir() {
      if (!this.cliente || !this.cliente.connected) return;
      if (this.suscripcion) this.cliente.unsubscribe(this.suscripcion);
      if (!this.patron) return;
      this.cliente.subscribe(this.patron, { qos: 0 });
      this.suscripcion = this.patron;
      this.recibidos.unshift({
        hora: util.hora(), topic: "—", carga: `suscrito a ${this.patron}`, clave: Math.random(),
      });
    },
  },

  template: `
<section class="vista">
  <header class="vista-cabecera">
    <h2>Explorador de topics</h2>
    <p class="intro">
      Tu navegador está conectado al broker por WebSocket: <strong>es un suscriptor
      más</strong>, igual que cualquier dispositivo. Cambia el patrón y observa qué
      topics coinciden y qué mensajes te llegan.
    </p>
  </header>

  <div class="controles">
    <label>Patrón de suscripción
      <input type="text" v-model="patron" size="34" @change="suscribir">
    </label>
    <button class="btn btn-secundario" @click="suscribir">Suscribirse</button>
    <span class="pastilla" :class="conectado ? 'pastilla-ok' : 'pastilla-mal'">
      navegador: {{ conectado ? 'suscrito al broker' : 'desconectado' }}
    </span>
  </div>

  <div class="rejilla-2">
    <div>
      <h3>Topics vistos en el broker</h3>
      <ul class="lista-topics">
        <li v-for="t in topics" :key="t" :class="{ coincide: coincide(t) }">
          <span>{{ t }}</span>
          <span class="cuenta">{{ tienda.estado.topics[t].mensajes }}</span>
        </li>
      </ul>
    </div>
    <div>
      <h3>Mensajes que coinciden con tu patrón</h3>
      <div class="consola">
        <div v-for="m in recibidos" :key="m.clave">{{ m.hora }}  {{ m.topic }}  {{ m.carga }}</div>
      </div>
    </div>
  </div>
</section>`,
};
