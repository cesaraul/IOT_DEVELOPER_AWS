/* Vista "HTTP paso a paso": solo HTTP, sin comparaciones y sin MQTT. */

window.Componentes = window.Componentes || {};

window.Componentes.VistaHttpPasos = {
  data() {
    return {
      guiones: GUIONES.http,
      elegido: GUIONES.http[0].id,
      codigos: [
        { codigo: "200 / 201", significa: "Recibido", decision: "Borrar la muestra de la cola local", tono: "ok" },
        { codigo: "400", significa: "Mi mensaje está mal formado", decision: "No reintentar: es mi bug. Registrar y descartar", tono: "mal" },
        { codigo: "401 / 403", significa: "Credenciales rechazadas", decision: "No reintentar en bucle: renovar el token o alertar", tono: "mal" },
        { codigo: "404", significa: "La ruta no existe", decision: "Error de configuración, no de red", tono: "mal" },
        { codigo: "429", significa: "Me están limitando", decision: "Esperar y bajar la frecuencia de envío", tono: "aviso" },
        { codigo: "5xx", significa: "El servidor falló", decision: "Reintentar con backoff exponencial + jitter", tono: "aviso" },
        { codigo: "(timeout)", significa: "No sé si llegó", decision: "Reintentar… y aquí nacen los duplicados", tono: "aviso" },
      ],
    };
  },

  computed: {
    guion() {
      return this.guiones.find((g) => g.id === this.elegido);
    },
  },

  template: `
<section class="vista">
  <header class="vista-cabecera">
    <h2>HTTP, paso a paso</h2>
    <p class="intro">
      Antes de comparar nada: qué ocurre <strong>exactamente</strong> cuando un
      dispositivo envía una medición por HTTP. Elige un escenario y míralo mensaje a
      mensaje. El contador de la derecha va sumando lo que de verdad viaja por la red.
    </p>
  </header>

  <div class="escenarios">
    <button v-for="g in guiones" :key="g.id"
            class="escenario" :class="{ activo: elegido === g.id }"
            @click="elegido = g.id">
      <strong>{{ g.titulo }}</strong>
      <small>{{ g.resumen }}</small>
    </button>
  </div>

  <diagrama-secuencia :guion="guion" :key="guion.id"></diagrama-secuencia>

  <h3>Los códigos de estado, leídos como decisiones de tu firmware</h3>
  <p class="intro">
    Un dispositivo no tiene pantalla ni a nadie mirándolo. Cada código de respuesta
    es una bifurcación en el código que escribes.
  </p>
  <table class="tabla tabla-codigos">
    <thead>
      <tr><th>Código</th><th>Qué significa</th><th>Qué debe hacer el dispositivo</th></tr>
    </thead>
    <tbody>
      <tr v-for="c in codigos" :key="c.codigo" :class="'tono-' + c.tono">
        <td><code>{{ c.codigo }}</code></td>
        <td>{{ c.significa }}</td>
        <td>{{ c.decision }}</td>
      </tr>
    </tbody>
  </table>

  <p class="nota">
    Todo esto es una reconstrucción didáctica. Para ver el tráfico real de tu propio
    cliente, usa el <strong>Inspector de paquetes</strong> del laboratorio en vivo.
  </p>
</section>`,
};
