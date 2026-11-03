/* Vista "MQTT paso a paso": solo MQTT, sin comparaciones y sin HTTP. */

window.Componentes = window.Componentes || {};

window.Componentes.VistaMqttPasos = {
  data() {
    return {
      guiones: GUIONES.mqtt,
      elegido: GUIONES.mqtt[0].id,
      niveles: [
        { parte: "fablab", papel: "sitio" },
        { parte: "planta1", papel: "zona" },
        { parte: "tanque-03", papel: "dispositivo" },
        { parte: "telemetria", papel: "tipo de dato" },
      ],
      pruebas: [
        { patron: "fablab/planta1/tanque-03/telemetria", coincide: true, nota: "exacto" },
        { patron: "fablab/+/+/telemetria", coincide: true, nota: "+ absorbe un nivel cada uno" },
        { patron: "fablab/planta1/#", coincide: true, nota: "# se lleva todo lo que cuelga" },
        { patron: "fablab/+/telemetria", coincide: false, nota: "+ es UN nivel, no dos" },
        { patron: "fablab/#/telemetria", coincide: false, nota: "# solo puede ir al final" },
      ],
      qos: [
        { nivel: "QoS 0", garantia: "A lo más una vez", paquetes: "1", uso: "Telemetría frecuente: si se pierde una muestra, la siguiente llega enseguida" },
        { nivel: "QoS 1", garantia: "Al menos una vez", paquetes: "2", uso: "Comandos, alarmas y eventos. Puede duplicar: tu payload necesita identificador" },
        { nivel: "QoS 2", garantia: "Exactamente una vez", paquetes: "4", uso: "Casi nunca. AWS IoT Core ni siquiera lo soporta" },
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
    <h2>MQTT, paso a paso</h2>
    <p class="intro">
      MQTT no es HTTP optimizado: es otra forma de plantear el problema. En vez de
      pedir, te suscribes. Aquí tienes cada mecanismo por separado, desde el CONNECT
      hasta el testamento.
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

  <div class="rejilla-2">
    <div class="tarjeta">
      <h3>Anatomía de un topic</h3>
      <p class="nota">De lo general a lo específico. Estructura en el topic, datos en el payload.</p>
      <div class="topic-anatomia">
        <div v-for="(n, i) in niveles" :key="n.parte" class="nivel">
          <code>{{ n.parte }}</code>
          <small>{{ n.papel }}</small>
          <span v-if="i < niveles.length - 1" class="barra-nivel">/</span>
        </div>
      </div>
      <table class="tabla">
        <tbody>
          <tr v-for="p in pruebas" :key="p.patron">
            <td><code>{{ p.patron }}</code></td>
            <td :class="p.coincide ? 'tono-ok' : 'tono-mal'">
              {{ p.coincide ? '✓ coincide' : '✗ no coincide' }}
            </td>
            <td class="nota">{{ p.nota }}</td>
          </tr>
        </tbody>
      </table>
      <p class="nota">
        Cambiar el esquema de topics con 500 dispositivos en campo significa actualizar
        firmware. Y en AWS, los permisos se escriben sobre estos mismos topics.
      </p>
    </div>

    <div class="tarjeta">
      <h3>Los tres niveles de QoS</h3>
      <table class="tabla">
        <thead>
          <tr><th>Nivel</th><th>Garantía</th><th>Paquetes</th></tr>
        </thead>
        <tbody>
          <tr v-for="q in qos" :key="q.nivel">
            <td><strong>{{ q.nivel }}</strong></td>
            <td>{{ q.garantia }}</td>
            <td>{{ q.paquetes }}</td>
          </tr>
        </tbody>
      </table>
      <ul class="lista-notas">
        <li v-for="q in qos" :key="q.nivel"><strong>{{ q.nivel }}:</strong> {{ q.uso }}</li>
      </ul>
      <p class="nota">
        Y el matiz que casi nadie enseña: <strong>el QoS es por salto</strong>. Se negocia
        entre cliente y broker, y otra vez entre broker y suscriptor. Publicar con QoS 2
        no garantiza que el suscriptor lo reciba con QoS 2 si él se suscribió con QoS 0.
      </p>
    </div>
  </div>

  <p class="nota">
    Para ver estos mismos mecanismos con un broker de verdad, pasa al
    <strong>laboratorio en vivo</strong>: ahí el tráfico es real.
  </p>
</section>`,
};
