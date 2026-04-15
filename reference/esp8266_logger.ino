#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include "esp8266_secrets.h"

ESP8266WebServer server(80);

const int NUM_SAMPLES = 50;
const float OFFSET = 17.0;
// SCALE = RealVoltage / (ADCreading - OFFSET)
// Example: 1.592 V / (552 - 17) ≈ 0.002975 V per ADC count
const float SCALE  = 0.002975;

unsigned long lastPostMs = 0;
unsigned long postIntervalMs = 2000;
unsigned long lastConfigFetchMs = 0;
const unsigned long CONFIG_FETCH_INTERVAL_MS = 5000;

void updateConfigFromServer()
{
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClient client;
  HTTPClient http;

  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/device-config";
  if (!http.begin(client, url)) return;

  int code = http.GET();
  if (code >= 200 && code < 300)
  {
    String body = http.getString();

    int enabledPos = body.indexOf("enabled=");
    if (enabledPos >= 0)
    {
      int enabledValue = body.substring(enabledPos + 8, body.indexOf('\n', enabledPos)).toInt();
      if (enabledValue == 0)
      {
        postIntervalMs = 0;
      }
    }

    int intervalPos = body.indexOf("interval=");
    if (intervalPos >= 0)
    {
      int lineEnd = body.indexOf('\n', intervalPos);
      if (lineEnd < 0) lineEnd = body.length();

      unsigned long intervalSeconds = body.substring(intervalPos + 9, lineEnd).toInt();
      if (intervalSeconds < 1) intervalSeconds = 1;

      if (body.indexOf("enabled=1") >= 0)
      {
        postIntervalMs = intervalSeconds * 1000UL;
      }
    }
  }

  http.end();
}

float readADC(int samples)
{
  long sum = 0;
  for (int i = 0; i < samples; i++)
  {
    sum += analogRead(A0);
    delay(2);
  }
  return sum / (float)samples;
}

float readVoltageFromAdc(float adcAvg)
{
  float corrected = adcAvg - OFFSET;
  float voltage = corrected * SCALE;
  if (voltage < 0) voltage = 0;
  return voltage;
}

float readVoltage()
{
  float adcAvg = readADC(NUM_SAMPLES);
  return readVoltageFromAdc(adcAvg);
}

bool postReading(float voltage, float adcAvg)
{
  if (WiFi.status() != WL_CONNECTED) return false;

  WiFiClient client;
  HTTPClient http;

  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/ingest";
  if (!http.begin(client, url)) return false;

  http.addHeader("Content-Type", "application/json");

  String body = "{";
  body += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  body += "\"voltage\":" + String(voltage, 3) + ",";
  body += "\"adc\":" + String(adcAvg, 1);
  body += "}";

  int code = http.POST(body);
  String resp = http.getString();
  http.end();

  Serial.print("POST ");
  Serial.print(url);
  Serial.print(" code=");
  Serial.print(code);
  Serial.print(" resp=");
  Serial.println(resp);

  return (code >= 200 && code < 300);
}

void handleRoot()
{
  float voltage = readVoltage();

  String html = "<!DOCTYPE html><html><head>";
  html += "<meta http-equiv='refresh' content='1'/>";
  html += "<style>body{font-family:Arial;text-align:center;margin-top:50px;}</style>";
  html += "</head><body>";
  html += "<h1>ESP8266 Voltage Monitor</h1>";
  html += "<h2>";
  html += String(voltage, 3);
  html += " V</h2>";
  html += "<p>Posting to: http://";
  html += SERVER_HOST;
  html += ":";
  html += String(SERVER_PORT);
  html += "/ingest</p>";
  html += "</body></html>";

  server.send(200, "text/html", html);
}

void setup()
{
  Serial.begin(115200);
  delay(200);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(300);
    Serial.print(".");
  }

  Serial.println("\nConnected");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.begin();
}

void loop()
{
  server.handleClient();

  unsigned long now = millis();
  if (now - lastConfigFetchMs >= CONFIG_FETCH_INTERVAL_MS)
  {
    lastConfigFetchMs = now;
    updateConfigFromServer();
  }

  if (postIntervalMs > 0 && now - lastPostMs >= postIntervalMs)
  {
    lastPostMs = now;

    float adcAvg = readADC(NUM_SAMPLES);
    float voltage = readVoltageFromAdc(adcAvg);

    postReading(voltage, adcAvg);
  }
}
