/*
 * Device Shadow en un ESP32 — el mismo laboratorio, pero con un LED de verdad.
 *
 * QUÉ HACE
 *   Lo mismo que shadow_dispositivo.py, línea por línea:
 *
 *     TELEMETRÍA   publica nivel y temperatura en
 *                  fablab/planta1/TU-ID/telemetria
 *     ESTADO       obedece a su shadow: la bomba (el LED de la placa), el
 *                  umbral de alarma y cada cuántos segundos transmite
 *
 *   Y la gracia: **enciendes el LED desde la consola de AWS**, aunque la
 *   placa estuviera desenchufada cuando diste la orden. Al arrancar
 *   pregunta qué debía ser, y obedece.
 *
 * ANTES DE EMPEZAR
 *   1. Genera tus certificados, desde labs/04-device-shadow:
 *
 *          docker compose run --rm dispositivo python generar_secretos.py
 *
 *      Eso crea secretos.h aquí al lado. Ábrelo en el IDE (aparece como
 *      otra pestaña) y escribe tu WiFi.
 *
 *   2. Librerías (Gestor de librerías del IDE de Arduino):
 *          - PubSubClient, de Nick O'Leary
 *          - ArduinoJson, de Benoit Blanchon   (versión 7)
 *
 *   3. Placa: "ESP32 Dev Module".
 *
 *   4. APAGA el shadow_dispositivo.py de tu laptop antes de encender la
 *      placa. Los dos se identifican con el mismo nombre y AWS expulsa a
 *      uno de los dos, una y otra vez.
 *
 * LAS DOS TRAMPAS DE HACER ESTO EN UN MICRO
 *   Son las que hacen que este sketch no sea una traducción trivial del
 *   Python, y las dos fallan en silencio:
 *
 *   1. EL BUFFER DE MQTT. PubSubClient trae 256 bytes por defecto, y un
 *      documento de shadow pasa del kilobyte. Los mensajes que no caben
 *      **se descartan sin aviso**: la placa queda conectada y sorda. Por
 *      eso abajo hay un setBufferSize().
 *
 *   2. LA FECHA. Un certificado tiene periodo de validez. Si el reloj del
 *      chip está en 1970, AWS rechaza la conexión sin explicar por qué.
 *      Por eso se sincroniza la hora por NTP antes de conectar.
 *
 * LAS TRES REGLAS DEL SHADOW
 *   - El dispositivo escribe 'reported'. Nunca 'desired'.
 *   - La aplicación escribe 'desired'. Nunca 'reported'.
 *   - El 'delta' no lo escribe nadie: lo calcula AWS.
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>

#include "secretos.h"

// Nombres cortos para lo que viene de secretos.h.
#define WIFI_SSID      SECRETO_WIFI_SSID
#define WIFI_PASSWORD  SECRETO_WIFI_PASSWORD
#define AWS_ENDPOINT   SECRETO_AWS_ENDPOINT
#define ID             SECRETO_DISPOSITIVO_ID
#define AWS_ROOT_CA    SECRETO_ROOT_CA
#define CERTIFICADO    SECRETO_CERTIFICADO
#define LLAVE_PRIVADA  SECRETO_LLAVE_PRIVADA

// El LED de la placa hace de bomba. En la mayoría de los ESP32 Dev Module
// está en el GPIO 2; si el tuyo no enciende, prueba el 2, el 5 o mira el
// esquema de tu placa.
const int PIN_BOMBA = 2;

// ------------------------------------------------- el estado (va al shadow)
// Pocas cosas, cambian poco, y deben sobrevivir a un apagón.

bool bombaEncendida = false;
int  umbral         = 80;   // a partir de este nivel, alarma
int  intervalo      = 5;    // segundos entre transmisiones

// ------------------------------------------- la realidad física (se mide)
// Esto NO va al shadow: es una medición. Cambia a cada rato y lo que
// interesa de ella es la serie, no el último valor.

float nivel = 50.0;

// ------------------------------------------------------------------ topics
// Se arman en setup() porque llevan dentro el nombre de tu objeto.

char tTelemetria[96];
char tUpdate[96], tUpdateAceptado[96], tUpdateRechazado[96], tDelta[96];
char tGet[96], tGetAceptado[96], tGetRechazado[96];

WiFiClientSecure red;
PubSubClient mqtt(red);

bool          estadoListo    = false;  // ¿ya sabemos qué debemos ser?
int           peticiones     = 0;      // cuántas veces hemos pedido el /get
unsigned long tSuscrito      = 0;
unsigned long ultimoEnvio    = 0;

// ------------------------------------------------------------------ Wi-Fi

void conectarWifi() {
  Serial.printf("Conectando a %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nConectado. Mi IP es %s\n", WiFi.localIP().toString().c_str());
}

// Sin hora correcta, los certificados parecen caducados y AWS rechaza todo.
void sincronizarHora() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("Sincronizando la hora");
  time_t ahora = time(nullptr);
  while (ahora < 1700000000) {   // cualquier fecha posterior a 2023
    delay(500);
    Serial.print(".");
    ahora = time(nullptr);
  }
  Serial.printf("\nHora lista: %s", ctime(&ahora));
}

// -------------------------------------------------------------- el estado

void aplicar(JsonObjectConst cambios) {
  // 'cambios' trae solo lo que hay que cambiar, no el estado completo: AWS
  // manda únicamente los campos que difieren.

  if (cambios["bomba"].is<const char*>()) {
    bombaEncendida = strcmp(cambios["bomba"], "encendida") == 0;
    // AQUÍ está la acción física de verdad. Primero se actúa; solo después
    // se reporta. Reportar algo que no hiciste es la peor mentira que puede
    // contar un dispositivo.
    digitalWrite(PIN_BOMBA, bombaEncendida ? HIGH : LOW);
    Serial.printf("  bomba -> %s\n", bombaEncendida ? "encendida" : "apagada");
  }

  if (cambios["umbral"].is<int>()) {
    umbral = cambios["umbral"];
    Serial.printf("  umbral -> %d\n", umbral);
  }

  if (cambios["intervalo"].is<int>()) {
    intervalo = cambios["intervalo"];
    Serial.printf("  intervalo -> %d s\n", intervalo);
  }
}

void reportar() {
  // Fíjate en la envoltura {"state":{"reported":{...}}}. Es obligatoria, y
  // olvidarla es el error número uno con shadows.
  JsonDocument doc;
  JsonObject rep = doc["state"]["reported"].to<JsonObject>();
  rep["bomba"]     = bombaEncendida ? "encendida" : "apagada";
  rep["umbral"]    = umbral;
  rep["intervalo"] = intervalo;

  char carga[256];
  serializeJson(doc, carga, sizeof(carga));
  mqtt.publish(tUpdate, carga);
  Serial.printf("  reportado: %s\n", carga);
}

void pedirEstado() {
  // "AWS, ¿qué debería ser yo?". La respuesta llega por tGetAceptado, o por
  // tGetRechazado con un 404 si el shadow todavía no existe.
  Serial.println("Preguntando por mi estado...");
  mqtt.publish(tGet, "");
  peticiones++;
  tSuscrito = millis();
}

// ----------------------------------------------------------- la telemetría

void transmitir() {
  // El nivel depende de la bomba: por eso, cuando cambias el shadow, lo ves
  // en los datos. El estado es la perilla; la telemetría es el efecto.
  if (bombaEncendida) {
    nivel += random(20, 60) / 10.0;
  } else {
    nivel -= random(10, 40) / 10.0;
  }
  if (nivel < 0)   nivel = 0;
  if (nivel > 100) nivel = 100;

  float temp = random(180, 360) / 10.0;
  bool alarma = nivel > umbral;

  char carga[128];
  snprintf(carga, sizeof(carga),
           "{\"nivel\":%.1f,\"temp\":%.1f,\"alarma\":%s}",
           nivel, temp, alarma ? "true" : "false");

  mqtt.publish(tTelemetria, carga);
  Serial.printf("  tx  %s\n", carga);
}

// ---------------------------------------------------------------- recibir

void alRecibir(char* topic, byte* carga, unsigned int largo) {
  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, carga, largo);

  if (error) {
    // Si ves esto, lo más probable es que el mensaje no cupiera en el buffer
    // de MQTT y llegara cortado. Sube el setBufferSize() de setup().
    Serial.printf("JSON ilegible (%s). ¿Buffer pequeño?\n", error.c_str());
    return;
  }

  // --- La respuesta a nuestro /get ---------------------------------------
  if (strcmp(topic, tGetAceptado) == 0) {
    JsonObjectConst pendiente = doc["state"]["delta"];

    if (!pendiente.isNull()) {
      // Mientras estábamos apagados, alguien pidió algo que no hemos hecho.
      Serial.println("\nHabía algo pendiente mientras estaba apagado:");
      aplicar(pendiente);
    } else {
      Serial.println("Nada pendiente: ya soy lo que se me pidió.");
    }

    reportar();
    estadoListo = true;
    Serial.printf("\nTransmitiendo en %s cada %d s.\n\n", tTelemetria, intervalo);
  }

  // --- Todavía no existe --------------------------------------------------
  else if (strcmp(topic, tGetRechazado) == 0) {
    if (doc["code"] == 404) {
      // Normal la primera vez: el shadow no se crea hasta que alguien
      // escribe en él. Lo creamos nosotros, reportando lo que somos.
      Serial.println("Todavía no tengo shadow. Lo creo con mi estado actual.");
      reportar();
      estadoListo = true;
      Serial.printf("\nTransmitiendo en %s cada %d s.\n\n", tTelemetria, intervalo);
    } else {
      Serial.printf("AWS rechazó mi consulta: código %d\n", (int)doc["code"]);
    }
  }

  // --- Una orden nueva, estando encendidos --------------------------------
  else if (strcmp(topic, tDelta) == 0) {
    Serial.println("\nOrden recibida:");
    aplicar(doc["state"]);
    reportar();
    Serial.println();
  }

  // --- AWS confirma --------------------------------------------------------
  else if (strcmp(topic, tUpdateAceptado) == 0) {
    Serial.printf("  (shadow guardado, versión %ld)\n", (long)doc["version"]);
  }

  // --- AWS no lo guardó ----------------------------------------------------
  else if (strcmp(topic, tUpdateRechazado) == 0) {
    Serial.printf("  AWS RECHAZÓ la actualización: código %d\n", (int)doc["code"]);
    Serial.println("  Un 400 suele ser JSON mal formado; un 409, que alguien");
    Serial.println("  escribió antes que tú y tu versión ya estaba vieja.");
  }
}

// ----------------------------------------------------------------- conectar

void conectarAws() {
  while (!mqtt.connected()) {
    Serial.printf("Conectando a %s ...\n", AWS_ENDPOINT);

    if (mqtt.connect(ID)) {
      Serial.println("Conectado a AWS IoT Core.\n");

      // Primero suscribirse a las respuestas, siempre. Si publicaras el
      // /get antes, la respuesta saldría al topic sin que nadie la
      // escuchara y la perderías, sin ningún error que lo explique.
      //
      // Nada de comodines aquí ($aws/things/X/shadow/#): AWS se reserva
      // añadir topics nuevos a esa estructura, y el día que lo haga tu
      // dispositivo recibiría mensajes que no sabe interpretar.
      mqtt.subscribe(tGetAceptado);
      mqtt.subscribe(tGetRechazado);
      mqtt.subscribe(tDelta);
      mqtt.subscribe(tUpdateAceptado);
      mqtt.subscribe(tUpdateRechazado);

      // Le damos un respiro al servidor para que registre las suscripciones
      // antes de preguntar. PubSubClient no avisa de cuándo AWS las
      // confirma, así que esperamos un poco y, si no hay respuesta,
      // volvemos a preguntar desde loop().
      estadoListo = false;
      peticiones  = 0;
      tSuscrito   = millis();

      for (int i = 0; i < 20; i++) {
        mqtt.loop();
        delay(50);
      }
      pedirEstado();

    } else {
      // -2 : certificados mal pegados, hora incorrecta o endpoint equivocado.
      //  5 : la politica no te deja conectarte con ese client-id, o hay
      //      otro cliente usando el mismo nombre (¿el script de tu laptop?).
      Serial.printf("Falló (código %d). Reintento en 5 s.\n", mqtt.state());
      delay(5000);
    }
  }
}

// ------------------------------------------------------------------ sketch

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(PIN_BOMBA, OUTPUT);
  digitalWrite(PIN_BOMBA, LOW);

  // Los topics del shadow los impone AWS y llevan dentro el nombre de tu
  // objeto. El de telemetría lo inventaste tú en el laboratorio 03.
  snprintf(tTelemetria,      sizeof(tTelemetria),      "fablab/planta1/%s/telemetria", ID);
  snprintf(tUpdate,          sizeof(tUpdate),          "$aws/things/%s/shadow/update", ID);
  snprintf(tUpdateAceptado,  sizeof(tUpdateAceptado),  "$aws/things/%s/shadow/update/accepted", ID);
  snprintf(tUpdateRechazado, sizeof(tUpdateRechazado), "$aws/things/%s/shadow/update/rejected", ID);
  snprintf(tDelta,           sizeof(tDelta),           "$aws/things/%s/shadow/update/delta", ID);
  snprintf(tGet,             sizeof(tGet),             "$aws/things/%s/shadow/get", ID);
  snprintf(tGetAceptado,     sizeof(tGetAceptado),     "$aws/things/%s/shadow/get/accepted", ID);
  snprintf(tGetRechazado,    sizeof(tGetRechazado),    "$aws/things/%s/shadow/get/rejected", ID);

  conectarWifi();
  sincronizarHora();

  red.setCACert(AWS_ROOT_CA);
  red.setCertificate(CERTIFICADO);
  red.setPrivateKey(LLAVE_PRIVADA);

  mqtt.setServer(AWS_ENDPOINT, 8883);
  mqtt.setCallback(alRecibir);

  // LA LÍNEA QUE SALVA EL LABORATORIO.
  //
  // PubSubClient trae un buffer de 256 bytes. El documento que devuelve
  // /get pasa del kilobyte, porque AWS le añade la metadata con la fecha de
  // cada campo. Lo que no cabe se descarta EN SILENCIO: la placa se queda
  // conectada, suscrita y sorda, sin un solo mensaje de error.
  //
  // 4 KB sobran para este laboratorio. Si algún día tu shadow crece, el
  // síntoma será exactamente ese silencio, y esta es la línea a tocar.
  mqtt.setBufferSize(4096);
}

void loop() {
  if (!mqtt.connected()) {
    conectarAws();
  }
  mqtt.loop();

  // Si AWS no nos ha contestado al /get, insistimos cada 5 segundos. Puede
  // pasar si la suscripción no estaba registrada del todo cuando
  // preguntamos.
  if (!estadoListo && millis() - tSuscrito > 5000) {
    if (peticiones < 5) {
      pedirEstado();
    } else {
      Serial.println("AWS no responde al /get. Revisa que tu política");
      Serial.println("autorice los topics $aws/things/.../shadow/*");
      tSuscrito = millis();
    }
  }

  // No transmitimos hasta saber qué estado debemos tener. Un equipo que
  // empieza a mandar datos antes de leer su configuración transmite con
  // valores que quizá ya no son los correctos.
  if (estadoListo && millis() - ultimoEnvio >= (unsigned long)intervalo * 1000UL) {
    ultimoEnvio = millis();
    transmitir();
  }
}
