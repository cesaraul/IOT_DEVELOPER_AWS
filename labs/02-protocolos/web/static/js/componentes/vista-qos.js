/* QoS y retención: el navegador como suscriptor de prueba. */

window.Componentes = window.Componentes || {};

window.Componentes.VistaQos = {
  data() {
    return {
      tienda,
      clientId: "alumno-01",
      sesionLimpia: false,
      conectado: false,
      cliente: null,
      registro: [],
    };
  },

  computed: {
    topic() {
      return `${this.tienda.estado.base_topic}/pruebas`;
    },
  },

  unmounted() {
    if (this.cliente) this.cliente.end(true);
  },

  methods: {
    anotar(texto, nivel = "info") {
      this.registro.unshift({ hora: util.hora(), texto, nivel, clave: Math.random() });
      if (this.registro.length > 100) this.registro.pop();
    },

    conectar() {
      if (this.cliente) this.cliente.end(true);
      this.cliente = mqtt.connect(`ws://${location.hostname}:9001`, {
        clientId: this.clientId,
        clean: this.sesionLimpia,
        reconnectPeriod: 0, // si no, se reconecta solo y arruina el experimento
      });
      this.cliente.on("connect", () => {
        this.conectado = true;
        this.cliente.subscribe(this.topic, { qos: 1 });
        this.anotar(`conectado con clean=${this.sesionLimpia} y suscrito con QoS 1`, "ok");
      });
      this.cliente.on("message", (topic, carga, paquete) => {
        this.anotar(
          `recibido  qos=${paquete.qos}${paquete.retain ? " retenido" : ""}  ${carga.toString()}`
        );
      });
      this.cliente.on("close", () => (this.conectado = false));
    },

    desconectar() {
      if (!this.cliente) return;
      this.cliente.end(true);
      this.anotar("suscriptor desconectado: publica ahora y vuelve a conectar", "aviso");
    },

    async publicar(qos, retener = false) {
      await util.enviar("/api/publicar", {
        topic: this.topic,
        carga: `mensaje qos=${qos}${retener ? " retenido" : ""} ${util.hora()}`,
        qos,
        retener,
      });
      this.anotar(`publicado con QoS ${qos}${retener ? " (retenido)" : ""}`, "aviso");
    },
  },

  template: `
<section class="vista">
  <header class="vista-cabecera">
    <h2>QoS y retención</h2>
    <p class="intro">
      Tu navegador es el suscriptor de prueba. Desconéctalo, publica mensajes y vuelve a
      conectarlo: comprobarás que lo que sobrevive depende del <strong>QoS</strong>
      <em>y</em> de la <strong>sesión persistente</strong>, no de uno solo de los dos.
    </p>
  </header>

  <div class="controles">
    <label>Client-id <input type="text" v-model="clientId" size="12"></label>
    <label><input type="checkbox" v-model="sesionLimpia"> Sesión limpia (<code>clean</code>)</label>
    <button class="btn btn-secundario" @click="conectar">Conectar</button>
    <button class="btn btn-secundario" @click="desconectar">Desconectar</button>
    <span class="pastilla" :class="conectado ? 'pastilla-ok' : 'pastilla-mal'">
      {{ conectado ? 'conectado' : 'desconectado' }}
    </span>
  </div>

  <div class="controles">
    <button class="btn btn-mqtt" @click="publicar(0)">Publicar con QoS 0</button>
    <button class="btn btn-mqtt" @click="publicar(1)">Publicar con QoS 1</button>
    <button class="btn btn-secundario" @click="publicar(1, true)">Publicar retenido</button>
    <span class="nota">al topic <code>{{ topic }}</code></span>
  </div>

  <div class="tarjeta">
    <h3>El experimento, en orden</h3>
    <ol class="lista-notas">
      <li>Conecta con <strong>sesión limpia desmarcada</strong> (<code>clean=false</code>).</li>
      <li>Desconecta el suscriptor.</li>
      <li>Publica un mensaje con QoS 0 y otro con QoS 1.</li>
      <li>Vuelve a conectar con el <strong>mismo client-id</strong>.</li>
      <li>Llega el de QoS 1 y no el de QoS 0: el broker no encola QoS 0.</li>
      <li>Repite todo con la sesión limpia marcada: ahora no llega ninguno.</li>
    </ol>
  </div>

  <div class="consola consola-alta">
    <div v-for="r in registro" :key="r.clave" :class="r.nivel">{{ r.hora }}  {{ r.texto }}</div>
  </div>
</section>`,
};
