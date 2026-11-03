/*
 * Ejemplo mínimo de MQTT en un ESP32.
 *
 * Hace las dos cosas:
 *   TRANSMITE  una muestra cada 5 segundos en  fablab/planta1/<ID>/telemetria
 *   RECIBE     órdenes en                      fablab/planta1/<ID>/comandos
 *
 * El broker es el que corre en tu computadora con Docker, así que el ESP32
 * y la computadora tienen que estar en la MISMA red Wi-Fi.
 *
 * Antes de subirlo, cambia las cuatro constantes de abajo.
 *
 * Librerías necesarias (Gestor de librerías del IDE de Arduino):
 *   - PubSubClient, de Nick O'Leary
 * Placa: "ESP32 Dev Module" (paquete esp32 de Espressif).
 */

#include <WiFi.h>
#include <PubSubClient.h>

// ----------------------------------------------------------- configuración

const char* WIFI_SSID     = "NOMBRE_DE_TU_WIFI";
const char* WIFI_PASSWORD = "CLAVE_DE_TU_WIFI";

// La IP de la computadora donde corre Docker, NO "localhost":
// para el ESP32, localhost sería él mismo.
// Windows: ipconfig    ·    macOS y Linux: ifconfig | ip addr
const char* MQTT_HOST = "192.168.1.100";
const int   MQTT_PORT = 1883;

// Cámbialo por algo único. Dos clientes con el mismo id se expulsan del broker.
const char* ID = "esp32-01";

// ---------------------------------------------------------------- internos

char topicTelemetria[64];
char topicComandos[64];

WiFiClient red;
PubSubClient mqtt(red);

unsigned long ultimoEnvio = 0;
unsigned long intervalo = 5000;  // milisegundos; un comando puede cambiarlo

// ------------------------------------------------------------------ Wi-Fi

void conectarWifi() {
  Serial.printf("Conectando a la red %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nConectado. Mi IP es %s\n", WiFi.localIP().toString().c_str());
}

// ------------------------------------------------------------------- MQTT

// Esto se ejecuta solo cuando LLEGA un mensaje: el broker nos lo empuja,
// no hace falta preguntar nada.
void alRecibir(char* topic, byte* carga, unsigned int largo) {
  char texto[128];
  unsigned int n = largo < sizeof(texto) - 1 ? largo : sizeof(texto) - 1;
  memcpy(texto, carga, n);
  texto[n] = '\0';

  Serial.printf("Comando recibido en %s: %s\n", topic, texto);

  // Si el mensaje es un número, lo tomamos como el nuevo intervalo en segundos.
  long segundos = atol(texto);
  if (segundos >= 1 && segundos <= 3600) {
    intervalo = segundos * 1000UL;
    Serial.printf("Nuevo intervalo: %ld s\n", segundos);
  }
}

void conectarMqtt() {
  while (!mqtt.connected()) {
    Serial.printf("Conectando al broker %s:%d ...\n", MQTT_HOST, MQTT_PORT);

    if (mqtt.connect(ID)) {
      Serial.println("Conectado al broker.");
      mqtt.subscribe(topicComandos);
      Serial.printf("Suscrito a %s\n", topicComandos);
    } else {
      // -2 suele ser red o IP equivocada; revisa el cortafuegos del PC.
      Serial.printf("Falló (código %d). Reintento en 3 s.\n", mqtt.state());
      delay(3000);
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
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(alRecibir);
}

void loop() {
  if (!mqtt.connected()) {
    conectarMqtt();
  }

  // Imprescindible: mantiene viva la conexión y entrega los mensajes que llegan.
  mqtt.loop();

  if (millis() - ultimoEnvio >= intervalo) {
    ultimoEnvio = millis();

    // Aquí leerías tu sensor de verdad. Por ahora, valores inventados.
    float temperatura = random(180, 360) / 10.0;
    int nivel = random(0, 101);

    char carga[96];
    snprintf(carga, sizeof(carga), "{\"temp\":%.1f,\"nivel\":%d}", temperatura, nivel);

    mqtt.publish(topicTelemetria, carga);
    Serial.printf("Enviado a %s: %s\n", topicTelemetria, carga);
  }
}
