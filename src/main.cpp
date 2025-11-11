#include <WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <DHT.h>

// -------------------- WiFi Configuration --------------------
const char* ssid = "Wokwi-GUEST";
const char* password = "";

// -------------------- HiveMQ Cloud Configuration --------------------
const char* mqtt_server = "af0dd70346c947d69803d51eb5952f8e.s1.eu.hivemq.cloud";
const int mqtt_port = 8883;
const char* mqtt_username = "Naufal";
const char* mqtt_password = "Febrianz123";

const char* topic_pub = "hidroponik/sensor";
const char* topic_sub = "hidroponik/pompa";

// -------------------- Sensor & Pin Configuration --------------------
#define DHTPIN 8
#define DHTTYPE DHT22
#define RELAY_PIN 7
#define LED_GREEN 5
#define LED_YELLOW 10
#define LED_RED 12
#define BUZZER 9

DHT dht(DHTPIN, DHTTYPE);

// -------------------- Secure WiFi & MQTT Client --------------------
WiFiClientSecure espClient;
PubSubClient client(espClient);

// -------------------- WiFi Connection --------------------
void setup_wifi() {
  Serial.print("Menghubungkan ke WiFi ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Terkoneksi!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

// -------------------- MQTT Callback --------------------
void callback(char* topic, byte* payload, unsigned int length) {
  payload[length] = '\0';
  String message = String((char*)payload);

  if (String(topic) == "hidroponik/pompa") {
    Serial.print("Pesan pompa: ");
    Serial.println(message);

    if (message == "ON") {
      digitalWrite(RELAY_PIN, HIGH);
      Serial.println("Pompa HIDUP");
    } else if (message == "OFF") {
      digitalWrite(RELAY_PIN, LOW);
      Serial.println("Pompa MATI");
    }
  }

  Serial.print("Pesan dari [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  if (String(topic) == topic_sub) {
    if (message == "ON") {
      digitalWrite(RELAY_PIN, HIGH);
      Serial.println("Pompa HIDUP");
    } else if (message == "OFF") {
      digitalWrite(RELAY_PIN, LOW);
      Serial.println("Pompa MATI");
    }
  }
}

// -------------------- MQTT Reconnect --------------------
void reconnect() {
  while (!client.connected()) {
    Serial.print("Menghubungkan ke MQTT...");
    if (client.connect("ESP32S2_Hidroponik", mqtt_username, mqtt_password)) {
      Serial.println("Terhubung ke HiveMQ Cloud!");
      client.subscribe(topic_sub);
    } else {
      Serial.print("Gagal, rc=");
      Serial.print(client.state());
      Serial.println(" mencoba lagi dalam 5 detik...");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  dht.begin();
  setup_wifi();

  espClient.setInsecure();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // --- Baca Sensor DHT ---
  float suhu = dht.readTemperature();
  float humidity = dht.readHumidity();

  if (isnan(suhu) || isnan(humidity)) {
    Serial.println("Gagal membaca sensor DHT!");
    return;
  }

  // --- Logika LED dan Buzzer ---
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED, LOW);
  digitalWrite(BUZZER, LOW);

  if (suhu > 35) {
    digitalWrite(LED_RED, HIGH);
    digitalWrite(BUZZER, HIGH);
  } else if (suhu >= 30 && suhu <= 35) {
    digitalWrite(LED_YELLOW, HIGH);
  } else {
    digitalWrite(LED_GREEN, HIGH);
  }

  // --- Kirim Data MQTT ---
  String payload = "{\"suhu\":" + String(suhu, 1) + ",\"humidity\":" + String(humidity, 1) + "}";
  client.publish(topic_pub, payload.c_str());

  Serial.println("Mengirim ke MQTT: " + payload);
  delay(5000);  // kirim setiap 5 detik
}
