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
 * ---------------------------------------------------------------------
 * DÓNDE ESTÁN TUS DATOS: en secretos.h, no aquí
 * ---------------------------------------------------------------------
 * En este archivo no hay nada tuyo: ni tu WiFi, ni tu endpoint, ni tus
 * certificados. Todo eso vive en secretos.h, que generas tú en un segundo
 * desde la carpeta labs/03-iot-core:
 *
 *     docker compose run --rm aws python generar_secretos.py
 *
 * El script lee tu carpeta 'certificados' y escribe secretos.h con los tres
 * certificados ya formateados. Luego abres el sketch en el IDE de Arduino:
 * secretos.h aparece como una pestaña al lado de esta, y lo único que
 * tienes que escribir a mano es tu WiFi.
 *
 * ¿Por qué separado? Porque este .ino se publica y tu llave privada no se
 * publica nunca. Un .ino con una llave dentro es un accidente esperando a
 * pasar: se manda por correo, se sube a un repositorio, se deja en un USB.
 * Separar el código de los secretos cuesta un archivo, y te ahorra tener
 * que revocar un certificado y volver a empezar.
 *
 * secretos.h está en el .gitignore. Este archivo no.
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <time.h>

#include "secretos.h"

// Nombres cortos para lo que viene de secretos.h, para que el resto del
// programa se lea exactamente igual que el de la clase 2. Si comparas los
// dos sketches, verás que de aquí abajo casi no cambia nada.
#define WIFI_SSID      SECRETO_WIFI_SSID
#define WIFI_PASSWORD  SECRETO_WIFI_PASSWORD
#define AWS_ENDPOINT   SECRETO_AWS_ENDPOINT
#define ID             SECRETO_DISPOSITIVO_ID
#define AWS_ROOT_CA    SECRETO_ROOT_CA
#define CERTIFICADO    SECRETO_CERTIFICADO
#define LLAVE_PRIVADA  SECRETO_LLAVE_PRIVADA

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
