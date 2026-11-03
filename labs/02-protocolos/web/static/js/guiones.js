/* Guiones de las animaciones paso a paso.
 *
 * Son datos, no código: cada escenario es una lista de mensajes con su tamaño
 * y su explicación. Si quieres añadir un escenario nuevo a la clase, basta con
 * agregarlo aquí.
 *
 * SOBRE LAS CIFRAS: los pasos de TCP y TLS incluyen las cabeceras IP y TCP,
 * porque es lo que de verdad viaja por la red, y son valores típicos (varían
 * según la pila y el certificado). Los mensajes HTTP y MQTT se miden a nivel
 * de aplicación, igual que en el inspector del laboratorio en vivo.
 */

const PETICION_CRUDA = `POST /telemetry HTTP/1.1
host: servidor.ejemplo:8000
user-agent: python-requests/2.32.3
accept-encoding: gzip, deflate
accept: */*
connection: keep-alive
authorization: Bearer demo-key
content-type: application/json
content-length: 26

{"temp":23.4,"nivel":87}`;

const GUIONES = {

  // ======================================================= HTTP
  http: [
    {
      id: "https-nueva",
      titulo: "Una muestra por HTTPS, conexión nueva",
      resumen: "El recorrido completo: saludo TCP, cifrado TLS, petición, respuesta y cierre.",
      actores: ["Dispositivo", "Servidor"],
      pasos: [
        { de: 0, a: 1, etiqueta: "SYN", bytes: 74, clase: "tcp",
          detalle: "El dispositivo pide abrir la conversación. Todavía no ha viajado ni un byte de tu medición: se está presentando." },
        { de: 1, a: 0, etiqueta: "SYN + ACK", bytes: 74, clase: "tcp",
          detalle: "El servidor acepta y responde con su propia petición de apertura." },
        { de: 0, a: 1, etiqueta: "ACK", bytes: 66, clase: "tcp",
          detalle: "Termina el saludo TCP: tres paquetes, 214 bytes y cero datos útiles. Esto ya consumió un viaje de ida y vuelta completo (1 RTT)." },
        { de: 0, a: 1, etiqueta: "TLS ClientHello", bytes: 517, clase: "tls",
          detalle: "Empieza la negociación del cifrado. El dispositivo propone versiones de TLS y algoritmos." },
        { de: 1, a: 0, etiqueta: "ServerHello + Certificado", bytes: 3400, clase: "tls",
          detalle: "Aquí viaja la cadena de certificados del servidor: es con diferencia el paquete más pesado de toda la conversación. Y es el que el dispositivo debe VERIFICAR, no simplemente aceptar." },
        { de: 0, a: 1, etiqueta: "Intercambio de claves + Finished", bytes: 230, clase: "tls",
          detalle: "El dispositivo aporta su parte del secreto y avisa de que ya cifra." },
        { de: 1, a: 0, etiqueta: "Finished", bytes: 280, clase: "tls",
          detalle: "Canal seguro listo. Llevamos ~4.4 KB gastados y la medición sigue sin salir del dispositivo." },
        { de: 0, a: 1, etiqueta: "POST /telemetry", bytes: 280, utiles: 26, clase: "app",
          crudo: PETICION_CRUDA,
          detalle: "Por fin viaja tu dato: 26 bytes dentro de una petición de 280. Las cabeceras ocupan más que la medición." },
        { de: 1, a: 0, etiqueta: "201 Created", bytes: 180, clase: "app",
          detalle: "El servidor confirma. El dispositivo ya puede borrar la muestra de su memoria." },
        { de: 0, a: 1, etiqueta: "FIN, ACK, FIN, ACK", bytes: 240, clase: "tcp",
          detalle: "Cerrar la conexión también cuesta: cuatro paquetes más. Y la siguiente muestra tendrá que repetir TODO esto desde el principio." },
      ],
      conclusion: "Más de 5 KB de tráfico para entregar 26 bytes de medición: una eficiencia del 0.5 %. Un dispositivo a batería paga esto en energía, y uno celular lo paga en plan de datos.",
    },
    {
      id: "https-keepalive",
      titulo: "La segunda muestra, con keep-alive",
      resumen: "La conexión ya está abierta. Mismo dato, una fracción del costo.",
      actores: ["Dispositivo", "Servidor"],
      pasos: [
        { de: 0, a: 1, etiqueta: "POST /telemetry", bytes: 280, utiles: 26, clase: "app",
          crudo: PETICION_CRUDA,
          detalle: "No hay SYN, ni certificados, ni negociación: la conexión del escenario anterior sigue viva gracias a la cabecera «connection: keep-alive»." },
        { de: 1, a: 0, etiqueta: "201 Created", bytes: 180, clase: "app",
          detalle: "Y ya está. Entrega completa." },
      ],
      conclusion: "460 bytes frente a los 5.000 del escenario anterior: reutilizar la conexión es la optimización más barata que existe en HTTP. En Python es la diferencia entre requests.post() suelto y requests.Session().",
    },
    {
      id: "http-503",
      titulo: "El servidor falla: 503 y backoff",
      resumen: "Qué hace un firmware bien escrito cuando el servidor no está disponible.",
      actores: ["Dispositivo", "Servidor"],
      pasos: [
        { de: 0, a: 1, etiqueta: "POST /telemetry", bytes: 280, utiles: 26, clase: "app",
          detalle: "Primer intento, con la muestra recién leída." },
        { de: 1, a: 0, etiqueta: "503 Service Unavailable", bytes: 150, clase: "error",
          detalle: "El servidor está sobrecargado. No es culpa del dispositivo: reintentar TIENE sentido, pero no de inmediato." },
        { de: 0, a: 0, etiqueta: "espera 1 s + jitter", bytes: 0, clase: "control",
          detalle: "Backoff exponencial: 1 s, 2 s, 4 s… El jitter (un pequeño retardo aleatorio) es lo que evita que 10.000 dispositivos reintenten en el mismo segundo y tumben otra vez al servidor que acaba de levantarse." },
        { de: 0, a: 1, etiqueta: "POST /telemetry (reintento 1)", bytes: 280, utiles: 26, clase: "app",
          detalle: "Segundo intento. Los mismos 280 bytes otra vez." },
        { de: 1, a: 0, etiqueta: "503 Service Unavailable", bytes: 150, clase: "error",
          detalle: "Sigue caído. La muestra se guarda en la cola local para no perderla." },
        { de: 0, a: 0, etiqueta: "espera 2 s + jitter", bytes: 0, clase: "control",
          detalle: "La espera se duplica. Si el corte durase horas, el dispositivo acabaría preguntando cada 30 segundos en vez de cada segundo." },
        { de: 0, a: 1, etiqueta: "POST /telemetry (reintento 2)", bytes: 280, utiles: 26, clase: "app",
          detalle: "Tercer intento." },
        { de: 1, a: 0, etiqueta: "201 Created", bytes: 180, clase: "app",
          detalle: "Entregado. Recién ahora se puede borrar la muestra de la cola." },
      ],
      conclusion: "1.320 bytes para entregar 26. El reintento es necesario, pero no es gratis: por eso importa distinguir qué códigos merecen reintento y cuáles no.",
    },
    {
      id: "http-400",
      titulo: "El error es tuyo: 400",
      resumen: "El caso en el que reintentar es exactamente lo que NO hay que hacer.",
      actores: ["Dispositivo", "Servidor"],
      pasos: [
        { de: 0, a: 1, etiqueta: "POST /telemetry", bytes: 262, utiles: 18, clase: "app",
          crudo: 'POST /telemetry HTTP/1.1\nauthorization: Bearer demo-key\ncontent-type: application/json\ncontent-length: 18\n\n{"temperatura":23}',
          detalle: "El firmware envía «temperatura» donde el servidor espera «temp»." },
        { de: 1, a: 0, etiqueta: "400 Bad Request", bytes: 140, clase: "error",
          detalle: "El servidor dice: tu mensaje está mal formado. Mañana estará igual de mal." },
        { de: 0, a: 0, etiqueta: "descartar y registrar", bytes: 0, clase: "control",
          detalle: "La decisión correcta es NO reintentar: registrar el error y descartar la muestra. Un bucle de reintentos ante un 400 vacía la batería repitiendo el mismo bug para siempre. Lo mismo vale para un 401: reintentar sin renovar la credencial no la va a arreglar." },
      ],
      conclusion: "La tabla de códigos no es teoría: es la lógica de decisión de tu firmware. 4xx = problema mío, no reintentar. 5xx y 429 = problema del otro lado, reintentar con backoff.",
    },
    {
      id: "http-polling",
      titulo: "Polling: el costo de preguntar",
      resumen: "Cómo se entera un dispositivo HTTP de que la nube quiere algo.",
      actores: ["Dispositivo", "Servidor"],
      pasos: [
        { de: 0, a: 1, etiqueta: "GET /config", bytes: 145, clase: "app",
          detalle: "El dispositivo pregunta: ¿hay novedades? Nadie le pidió nada; lo hace porque es la única forma que tiene de enterarse." },
        { de: 1, a: 0, etiqueta: '200 {"version":1}', bytes: 160, clase: "app",
          detalle: "No hay nada nuevo. Acabas de gastar 305 bytes para que te digan que no pasa nada." },
        { de: 0, a: 0, etiqueta: "espera 60 s", bytes: 0, clase: "control",
          detalle: "Mientras tanto, un operador cambia la configuración en la nube. El dispositivo no se entera: nadie puede llamarlo." },
        { de: 0, a: 1, etiqueta: "GET /config", bytes: 145, clase: "app",
          detalle: "Siguiente ronda de preguntas." },
        { de: 1, a: 0, etiqueta: '200 {"version":2, "intervalo_s":1}', bytes: 190, clase: "app",
          detalle: "Ahora sí llega el cambio. Pero llevaba 47 segundos esperando en el servidor." },
        { de: 0, a: 0, etiqueta: "aplica el cambio", bytes: 0, clase: "control",
          detalle: "Con un intervalo de 60 s, la latencia media de un comando es de 30 s y la peor de 60 s. Bajar el intervalo mejora la reacción y multiplica el tráfico: 10.000 dispositivos preguntando cada segundo son 10.000 peticiones por segundo que el servidor paga aunque no haya ninguna novedad." },
      ],
      conclusion: "No existe un intervalo bueno: es elegir entre gastar o responder tarde. Este es exactamente el problema que MQTT resuelve manteniendo la conexión abierta.",
    },
  ],

  // ======================================================= MQTT
  mqtt: [
    {
      id: "mqtt-conexion",
      titulo: "Conectarse y suscribirse",
      resumen: "Lo que ocurre una sola vez, al principio de todo.",
      actores: ["Dispositivo", "Broker"],
      pasos: [
        { de: 0, a: 1, etiqueta: "Handshake TCP + TLS", bytes: 4614, clase: "tls",
          detalle: "Sí: MQTT paga exactamente el mismo peaje que HTTPS. No hay magia. La diferencia es que lo paga UNA VEZ y después mantiene la conexión abierta durante días." },
        { de: 0, a: 1, etiqueta: "CONNECT", bytes: 62, clase: "control",
          crudo: 'CONNECT\n  protocolo    : MQTT 5\n  client-id    : tanque-03\n  keepalive    : 30 s\n  clean start  : false\n  testamento   : fablab/planta1/tanque-03/estado = "offline" (retenido)',
          detalle: "El paquete de presentación. Aquí se entrega el TESTAMENTO: el mensaje que el broker publicará si esta conexión muere sin despedirse. Se define al conectar, no después. Y el client-id debe ser único: si otro cliente usa el mismo, el broker expulsa a uno de los dos." },
        { de: 1, a: 0, etiqueta: "CONNACK", bytes: 4, clase: "control",
          detalle: "Cuatro bytes. La conexión queda establecida y, a partir de aquí, el broker puede hablar primero." },
        { de: 0, a: 1, etiqueta: "SUBSCRIBE fablab/planta1/tanque-03/comandos", bytes: 44, clase: "control",
          detalle: "El dispositivo se declara interesado en su topic de comandos, con QoS 1. Esto es lo que hace posible el push." },
        { de: 1, a: 0, etiqueta: "SUBACK (QoS concedido: 1)", bytes: 5, clase: "control",
          detalle: "El broker confirma y dice qué QoS concede, que puede ser MENOR del que pediste. Conviene mirarlo." },
      ],
      conclusion: "Después de estos cinco pasos la conexión queda abierta. Todo lo que venga después cuesta bytes contados, no kilobytes.",
    },
    {
      id: "mqtt-qos0",
      titulo: "PUBLISH con QoS 0",
      resumen: "La telemetría normal: un paquete y nada más.",
      actores: ["Dispositivo", "Broker"],
      pasos: [
        { de: 0, a: 1, etiqueta: "PUBLISH …/telemetria", bytes: 86, utiles: 26, clase: "app",
          crudo: 'PUBLISH (QoS 0)\n  cabecera fija      : 2 B\n  topic              : fablab/planta1/tanque-03/telemetria  (35 B)\n  payload            : {"temp":23.4,"nivel":87}  (26 B)\n  ------------------------------------\n  total en la red    : 86 B',
          detalle: "Dos bytes de cabecera, el nombre del topic y tu dato. Nadie confirma nada: «a lo más una vez». Si se pierde esta muestra, la siguiente llega en unos segundos." },
      ],
      conclusion: "86 bytes frente a los 5.000 de la primera petición HTTPS, y 54 de esos 86 son el nombre del topic. Acortar el topic a «fl/p1/t03/tl» bajaría el mensaje a ~45 bytes: en una flota celular grande, eso se acorta.",
    },
    {
      id: "mqtt-qos1",
      titulo: "QoS 1: «al menos una vez» (y el duplicado)",
      resumen: "Por qué el problema de los duplicados no desaparece con MQTT.",
      actores: ["Dispositivo", "Broker"],
      pasos: [
        { de: 0, a: 1, etiqueta: "PUBLISH (id 1, QoS 1)", bytes: 88, utiles: 26, clase: "app",
          detalle: "Igual que antes, más dos bytes con el identificador del paquete." },
        { de: 1, a: 0, etiqueta: "PUBACK (id 1)", bytes: 4, clase: "control",
          detalle: "Confirmado. El dispositivo ya puede olvidarse de esta muestra." },
        { de: 0, a: 1, etiqueta: "PUBLISH (id 2, QoS 1)", bytes: 88, utiles: 26, clase: "app",
          detalle: "Siguiente muestra. El broker la recibe y la reparte correctamente." },
        { de: 1, a: 0, etiqueta: "PUBACK (id 2)", bytes: 4, clase: "error", perdido: true,
          detalle: "…pero la confirmación se pierde por el camino. El broker cree que todo fue bien; el dispositivo cree que nada llegó." },
        { de: 0, a: 1, etiqueta: "PUBLISH (id 2, DUP)", bytes: 88, utiles: 26, clase: "app",
          detalle: "El dispositivo reenvía con el flag DUP activado. El broker, que ya la tenía, la vuelve a repartir: el mensaje ha llegado DOS VECES a los suscriptores." },
        { de: 1, a: 0, etiqueta: "PUBACK (id 2)", bytes: 4, clase: "control",
          detalle: "Ahora sí llega la confirmación." },
      ],
      conclusion: "«Al menos una vez» es literal. Por eso tu payload necesita su propio identificador de evento o su timestamp: la idempotencia que viste en HTTP sigue siendo responsabilidad tuya.",
    },
    {
      id: "mqtt-qos2",
      titulo: "QoS 2: «exactamente una vez»",
      resumen: "La garantía fuerte y lo que cuesta.",
      actores: ["Dispositivo", "Broker"],
      pasos: [
        { de: 0, a: 1, etiqueta: "PUBLISH (id 7, QoS 2)", bytes: 88, utiles: 26, clase: "app",
          detalle: "Primer paso de un diálogo de cuatro." },
        { de: 1, a: 0, etiqueta: "PUBREC (recibido)", bytes: 4, clase: "control",
          detalle: "El broker avisa de que lo tiene, pero todavía no lo entrega." },
        { de: 0, a: 1, etiqueta: "PUBREL (libéralo)", bytes: 4, clase: "control",
          detalle: "El dispositivo autoriza la entrega. Recién aquí el broker reparte el mensaje." },
        { de: 1, a: 0, etiqueta: "PUBCOMP (completado)", bytes: 4, clase: "control",
          detalle: "Cierre del diálogo. Nadie puede duplicarlo." },
      ],
      conclusion: "Cuatro paquetes y dos viajes de ida y vuelta por mensaje. Reservado para lo que no se puede repetir (una orden de pago, una factura). AWS IoT Core soporta QoS 0 y 1, no QoS 2: ahora sabes que no es una carencia grave.",
    },
    {
      id: "mqtt-enrutado",
      titulo: "El broker reparte: enrutado por topic",
      resumen: "Un publicador, varios suscriptores, y nadie se conoce.",
      actores: ["Dispositivo", "Broker", "Dashboard", "Alertas"],
      pasos: [
        { de: 2, a: 1, etiqueta: "SUBSCRIBE fablab/+/+/telemetria", bytes: 42, clase: "control",
          detalle: "El dashboard se suscribe con un comodín de un nivel: le interesa la telemetría de cualquier planta y cualquier dispositivo." },
        { de: 3, a: 1, etiqueta: "SUBSCRIBE fablab/planta1/#", bytes: 38, clase: "control",
          detalle: "El motor de alertas pide TODO lo de la planta 1: telemetría, estado y lo que se añada en el futuro. El comodín # solo puede ir al final." },
        { de: 0, a: 1, etiqueta: "PUBLISH …/telemetria", bytes: 86, utiles: 26, clase: "app",
          detalle: "El dispositivo publica UNA vez. No sabe cuántos suscriptores hay, ni si hay alguno. No le importa." },
        { de: 1, a: 2, etiqueta: "→ Dashboard (coincide)", bytes: 86, utiles: 26, clase: "app",
          detalle: "fablab/planta1/tanque-03/telemetria encaja con fablab/+/+/telemetria: cuatro niveles, los comodines absorben planta1 y tanque-03." },
        { de: 1, a: 3, etiqueta: "→ Alertas (coincide)", bytes: 86, utiles: 26, clase: "app",
          detalle: "También encaja con fablab/planta1/#. El broker entregó dos copias de un solo publish." },
      ],
      conclusion: "Para añadir mañana un tercer consumidor —un histórico, un modelo de predicción— no se toca el firmware de los 500 dispositivos: se suscribe y ya está. Eso es el desacople, y es la razón principal por la que MQTT domina en IoT.",
    },
    {
      id: "mqtt-keepalive",
      titulo: "Keepalive: el latido que mantiene el agujero abierto",
      resumen: "Cuatro bytes cada 30 segundos y por qué son imprescindibles.",
      actores: ["Dispositivo", "Broker"],
      pasos: [
        { de: 0, a: 1, etiqueta: "PINGREQ", bytes: 2, clase: "control",
          detalle: "Si no hay tráfico, el dispositivo manda dos bytes. No es un capricho: el router NAT y el firewall cierran las conexiones que parecen muertas, y con ellas se iría la posibilidad de recibir comandos." },
        { de: 1, a: 0, etiqueta: "PINGRESP", bytes: 2, clase: "control",
          detalle: "El broker responde. Además, este latido es lo que le permite DETECTAR que un dispositivo desapareció: si no llega nada en 1.5 veces el keepalive, lo da por muerto y dispara su testamento." },
      ],
      conclusion: "El keepalive es el precio de mantener la puerta abierta en los dos sentidos. Un keepalive corto detecta caídas antes y gasta más batería: es una decisión de diseño, no un valor por defecto.",
    },
    {
      id: "mqtt-retenido",
      titulo: "Retenido: el suscriptor que llega tarde",
      resumen: "Cómo ve el estado actual alguien que se conecta después.",
      actores: ["Dispositivo", "Broker", "Dashboard"],
      pasos: [
        { de: 0, a: 1, etiqueta: 'PUBLISH …/estado "online" (retain)', bytes: 48, utiles: 6, clase: "app",
          detalle: "El dispositivo publica su estado con el flag retain. El broker, además de repartirlo, lo GUARDA como último valor conocido de ese topic." },
        { de: 2, a: 1, etiqueta: "SUBSCRIBE …/estado", bytes: 40, clase: "control",
          detalle: "El dashboard se abre media hora después. Llega tardísimo a la fiesta." },
        { de: 1, a: 2, etiqueta: 'PUBLISH "online" (retenido)', bytes: 48, utiles: 6, clase: "app",
          detalle: "El broker se lo entrega AL INSTANTE, sin esperar a que el dispositivo publique de nuevo. Sin retain, el dashboard mostraría un hueco hasta el siguiente mensaje: si el dispositivo reporta cada 10 minutos, serían 10 minutos en blanco." },
      ],
      conclusion: "Retenido = «el estado actual de este topic», uno por topic y para todos los que se suscriban. No confundir con la sesión persistente, que es una cola privada de un cliente concreto.",
    },
    {
      id: "mqtt-sesion",
      titulo: "Sesión persistente: tu cola privada",
      resumen: "Qué pasa con los mensajes de un suscriptor que estaba desconectado.",
      actores: ["Dispositivo", "Broker", "Dashboard"],
      pasos: [
        { de: 2, a: 1, etiqueta: "CONNECT (clean start: false) + SUBSCRIBE QoS 1", bytes: 96, clase: "control",
          detalle: "El dashboard se identifica con su client-id y pide que el broker RECUERDE su sesión. Esta es la condición imprescindible: con clean start en true, nada de lo que sigue funciona." },
        { de: 2, a: 1, etiqueta: "DISCONNECT (se cierra el dashboard)", bytes: 2, clase: "control",
          detalle: "Despedida limpia. El broker conserva la suscripción asociada a ese client-id." },
        { de: 0, a: 1, etiqueta: "PUBLISH QoS 1 (muestra A)", bytes: 88, utiles: 26, clase: "app",
          detalle: "El dispositivo sigue publicando, ajeno a todo. El broker guarda el mensaje para el suscriptor ausente." },
        { de: 0, a: 1, etiqueta: "PUBLISH QoS 1 (muestra B)", bytes: 88, utiles: 26, clase: "app",
          detalle: "Y otra. La cola del dashboard crece." },
        { de: 2, a: 1, etiqueta: "CONNECT (clean start: false)", bytes: 94, clase: "control",
          detalle: "El dashboard vuelve. El broker reconoce su client-id y recupera la sesión." },
        { de: 1, a: 2, etiqueta: "PUBLISH A y B (de la cola)", bytes: 176, utiles: 52, clase: "app",
          detalle: "Recibe lo que se perdió mientras no estaba. Con QoS 0 no habría habido nada que entregar: el broker no encola QoS 0." },
      ],
      conclusion: "Hacen falta DOS cosas a la vez: QoS 1 o superior, y sesión persistente. Quien solo recuerda una de las dos se lleva una sorpresa en producción.",
    },
    {
      id: "mqtt-lwt",
      titulo: "Testamento: detectar un dispositivo caído",
      resumen: "Lo que HTTP no puede hacer de ninguna manera.",
      actores: ["Dispositivo", "Broker", "Dashboard"],
      pasos: [
        { de: 0, a: 1, etiqueta: 'CONNECT (will: …/estado = "offline")', bytes: 62, clase: "control",
          detalle: "Al conectarse, el dispositivo le deja al broker su mensaje de despedida. El broker lo guarda, sin publicarlo." },
        { de: 0, a: 1, etiqueta: 'PUBLISH …/estado "online" (retain)', bytes: 48, utiles: 6, clase: "app",
          detalle: "Y publica que está vivo, retenido, para quien llegue después." },
        { de: 0, a: 1, etiqueta: "✗ se va la energía", bytes: 0, clase: "error", perdido: true,
          detalle: "Corte eléctrico. No hay DISCONNECT, no hay despedida, no hay nada: la conexión simplemente desaparece. Si en cambio el dispositivo se cerrara ordenadamente, el testamento NO se dispararía: una desconexión limpia no es una caída." },
        { de: 1, a: 1, etiqueta: "el broker espera 1.5 × keepalive", bytes: 0, clase: "control",
          detalle: "Sin latidos ni tráfico, el broker lo da por muerto. Con keepalive de 30 s, lo detecta en unos 45." },
        { de: 1, a: 2, etiqueta: 'PUBLISH …/estado "offline" (retenido)', bytes: 48, utiles: 7, clase: "app",
          detalle: "Lo publica el BROKER, en nombre del dispositivo muerto. El dashboard se entera sin haber tenido que vigilar nada." },
      ],
      conclusion: "En HTTP esto no existe: habría que inventar heartbeats, guardarlos en el servidor y correr un proceso que detecte ausencias. Aquí son dos líneas de código al conectar.",
    },
  ],
};
