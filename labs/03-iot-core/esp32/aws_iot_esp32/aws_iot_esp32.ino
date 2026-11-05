/*
 * Conectar un ESP32 a AWS IoT Core — reto opcional, para hacer en casa.
 *
 * Es el mismo sketch de la clase 2 con tres cambios:
 *   - WiFiClientSecure en vez de WiFiClient (cifrado y certificados)
 *   - el endpoint de tu cuenta en vez de la IP de tu laptop
 *   - el puerto 8883 en vez del 1883
 *
 * Y una cosa que no existía antes: el ESP32 necesita saber la FECHA. Un
 * certificado tiene fecha de validez, así que si el reloj del chip está en
 * el año 1970 la conexión se rechaza. Por eso se sincroniza la hora por NTP
 * antes de conectar. Ese es el error más común, y no es nada evidente.
 *
 * Librerías (Gestor de librerías del IDE de Arduino):
 *   - PubSubClient, de Nick O'Leary
 * Placa: "ESP32 Dev Module".
 *
 * Antes de subirlo, rellena las secciones 1, 2 y 3.
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <time.h>

// ======================================================= 1. TU RED WIFI

const char* WIFI_SSID     = "NOMBRE_DE_TU_WIFI";
const char* WIFI_PASSWORD = "CLAVE_DE_TU_WIFI";

// ======================================================= 2. TU CUENTA AWS

// Consola de IoT Core -> Settings -> "Device data endpoint"
const char* AWS_ENDPOINT = "xxxxxxxxxxxxxx-ats.iot.us-east-1.amazonaws.com";

// El nombre de tu Thing. Debe coincidir con el de la consola.
const char* ID = "mi-dispositivo";

// ======================================================= 3. TUS CERTIFICADOS
//
// Abre cada archivo del connection kit con el Bloc de notas y pega su
// contenido COMPLETO entre las comillas, incluidas las líneas
// -----BEGIN ... ----- y -----END ... -----.

// AmazonRootCA1.pem
static const char AWS_ROOT_CA[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
PEGA AQUI EL CONTENIDO DE AmazonRootCA1.pem
-----END CERTIFICATE-----
)EOF";

// xxxxx-certificate.pem.crt
static const char CERTIFICADO[] PROGMEM = R"KEY(
-----BEGIN CERTIFICATE-----
PEGA AQUI EL CONTENIDO DE TU ARCHIVO -certificate.pem.crt
-----END CERTIFICATE-----
)KEY";

// xxxxx-private.pem.key
static const char LLAVE_PRIVADA[] PROGMEM = R"KEY(
-----BEGIN RSA PRIVATE KEY-----
PEGA AQUI EL CONTENIDO DE TU ARCHIVO -private.pem.key
-----END RSA PRIVATE KEY-----
)KEY";

// ---------------------------------------------------------------- internos

char topicTelemetria[80];
char topicComandos[80];

WiFiClientSecure red;
PubSubClient mqtt(red);

unsigned long ultimoEnvio = 0;
unsigned long intervalo = 5000;

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

// ------------------------------------------------------------------- MQTT

void alRecibir(char* topic, byte* carga, unsigned int largo) {
  char texto[128];
  unsigned int n = largo < sizeof(texto) - 1 ? largo : sizeof(texto) - 1;
  memcpy(texto, carga, n);
  texto[n] = '\0';
  Serial.printf("Comando en %s: %s\n", topic, texto);

  long segundos = atol(texto);
  if (segundos >= 1 && segundos <= 3600) {
    intervalo = segundos * 1000UL;
    Serial.printf("Nuevo intervalo: %ld s\n", segundos);
  }
}

void conectarAws() {
  while (!mqtt.connected()) {
    Serial.printf("Conectando a %s ...\n", AWS_ENDPOINT);

    if (mqtt.connect(ID)) {
      Serial.println("Conectado a AWS IoT Core.");
      mqtt.subscribe(topicComandos);
      Serial.printf("Suscrito a %s\n", topicComandos);
    } else {
      // -2 : certificados mal pegados, hora incorrecta o endpoint equivocado.
      // 5  : la politica no te deja conectarte con ese client-id.
      Serial.printf("Falló (código %d). Reintento en 5 s.\n", mqtt.state());
      delay(5000);
    }
  }
}

// ------------------------------------------------------------------ sketch

void setup() {
  Serial.begin(115200);
  delay(500);

  snprintf(topicTelemetria, sizeof(topicTelemetria), "fablab/planta1/%s/telemetria", ID);
  snprintf(topicComandos,  sizeof(topicComandos),  "fablab/planta1/%s/comandos",  ID);

  conectarWifi();
  sincronizarHora();

  red.setCACert(AWS_ROOT_CA);
  red.setCertificate(CERTIFICADO);
  red.setPrivateKey(LLAVE_PRIVADA);

  mqtt.setServer(AWS_ENDPOINT, 8883);
  mqtt.setCallback(alRecibir);
}

void loop() {
  if (!mqtt.connected()) {
    conectarAws();
  }
  mqtt.loop();

  if (millis() - ultimoEnvio >= intervalo) {
    ultimoEnvio = millis();

    float temperatura = random(180, 360) / 10.0;
    int nivel = random(0, 101);

    char carga[96];
    snprintf(carga, sizeof(carga), "{\"temp\":%.1f,\"nivel\":%d}", temperatura, nivel);

    mqtt.publish(topicTelemetria, carga);
    Serial.printf("Enviado: %s\n", carga);
  }
}
