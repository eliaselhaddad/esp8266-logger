---
marp: true
theme: default
paginate: true
title: ESP8266 Logger
description: Simple technical walkthrough of the ESP8266 voltage logger sketch
---

# ESP8266 Logger

Simple technical walkthrough of `reference/esp8266_logger.ino`

- Reads analog voltage on `A0`
- Hosts a tiny local web page
- Polls the server for config
- Posts measurements back as JSON

---

# 1. What This Device Does

The ESP8266 acts like a small sensor node:

1. Connect to Wi-Fi
2. Measure analog voltage
3. Convert ADC counts into volts
4. Show the current value in a browser
5. Send readings to a backend server
6. Ask the backend how often it should report

This makes the firmware both a sensor and a simple network client/server.

---

# 2. Main Building Blocks

```cpp
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPClient.h>
#include "esp8266_secrets.h"
```

- `ESP8266WiFi.h`: connects the board to Wi-Fi
- `ESP8266WebServer.h`: runs a local HTTP server on port `80`
- `ESP8266HTTPClient.h`: sends HTTP requests to another server
- `esp8266_secrets.h`: keeps Wi-Fi and backend settings outside the main sketch

The firmware depends on the ESP8266 Arduino core libraries plus one local config file.

---

# 3. Global State

```cpp
ESP8266WebServer server(80);

const int NUM_SAMPLES = 50;
const float OFFSET = 17.0;
const float SCALE  = 0.002975;

unsigned long lastPostMs = 0;
unsigned long postIntervalMs = 2000;
unsigned long lastConfigFetchMs = 0;
const unsigned long CONFIG_FETCH_INTERVAL_MS = 5000;
```

- `server(80)`: local web server listens on HTTP port 80
- `NUM_SAMPLES`: average multiple ADC reads to reduce noise
- `OFFSET` and `SCALE`: calibration values that map raw ADC counts to volts
- `lastPostMs` and `lastConfigFetchMs`: track timing without blocking the program

This is a common embedded pattern: keep a small amount of state and use `millis()` for scheduling.

---

# 4. Startup Flow in `setup()`

```cpp
void setup()
{
  Serial.begin(115200);
  delay(200);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(300);
    Serial.print(".");
  }

  server.on("/", handleRoot);
  server.begin();
}
```

- Start serial logging for debugging
- Connect to the configured Wi-Fi network
- Wait until the connection is ready
- Register a handler for `/`
- Start the embedded web server

After `setup()` completes, the board is online and ready to serve requests.

---

# 5. Reading the Analog Signal

```cpp
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
```

- `analogRead(A0)` returns a raw ADC number, not a voltage
- The code takes `50` samples and averages them
- A short `delay(2)` spreads samples slightly to reduce jitter

This is a lightweight noise-filtering technique that works well on small microcontrollers.

---

# 6. Converting ADC to Voltage

```cpp
float readVoltageFromAdc(float adcAvg)
{
  float corrected = adcAvg - OFFSET;
  float voltage = corrected * SCALE;
  if (voltage < 0) voltage = 0;
  return voltage;
}
```

The math is based on calibration:

- `OFFSET` removes baseline error
- `SCALE` converts corrected ADC counts into volts
- Negative results are clamped to `0`

So the firmware does not assume ideal hardware. It corrects the raw input using measured calibration values.

---

# 7. Local Web Interface

```cpp
void handleRoot()
{
  float voltage = readVoltage();
  String html = "<!DOCTYPE html><html><head>";
  html += "<meta http-equiv='refresh' content='1'/>";
  ...
  server.send(200, "text/html", html);
}
```

- When a browser opens `/`, the ESP8266 measures the voltage
- It builds an HTML page as a string
- The page refreshes every second
- The browser sees the live voltage and the backend target URL

This is useful for quick diagnostics without needing a separate app.

---

# 8. Posting Data to the Backend

```cpp
bool postReading(float voltage, float adcAvg)
{
  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/ingest";
  http.addHeader("Content-Type", "application/json");

  String body = "{";
  body += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  body += "\"voltage\":" + String(voltage, 3) + ",";
  body += "\"adc\":" + String(adcAvg, 1);
  body += "}";

  int code = http.POST(body);
  ...
}
```

- Build the backend URL from config values
- Set HTTP content type to JSON
- Send device ID, calculated voltage, and raw ADC average
- Log the HTTP response code to serial output

The backend receives both the processed value and the raw measurement, which is useful for debugging and recalibration.

---

# 9. Pulling Config From the Server

```cpp
void updateConfigFromServer()
{
  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/device-config";
  int code = http.GET();
  ...
  int enabledPos = body.indexOf("enabled=");
  int intervalPos = body.indexOf("interval=");
}
```

- The device calls `/device-config`
- It expects a simple text response
- It looks for `enabled=` and `interval=`
- `enabled=0` stops reporting
- `interval=<seconds>` changes how often readings are posted

This gives the backend some control over device behavior without reflashing firmware.

---

# 10. The Main Loop

```cpp
void loop()
{
  server.handleClient();

  unsigned long now = millis();
  if (now - lastConfigFetchMs >= CONFIG_FETCH_INTERVAL_MS)
  {
    updateConfigFromServer();
  }

  if (postIntervalMs > 0 && now - lastPostMs >= postIntervalMs)
  {
    postReading(voltage, adcAvg);
  }
}
```

- `server.handleClient()` keeps the local web server responsive
- `millis()` is used for timing instead of long blocking delays
- Config is fetched every 5 seconds
- Measurements are posted using the current interval

This is cooperative multitasking: one loop handles multiple jobs by checking timers.

---

# 11. Why This Design Works Well

- Simple control flow: `setup()` once, `loop()` forever
- Low memory usage: no RTOS, no complex framework
- Easy field debugging: serial logs plus local browser page
- Remote behavior control: server can enable/disable posting
- Basic calibration support: raw ADC becomes meaningful voltage

For a small ESP8266 project, this is a practical architecture with low overhead.

---

# 12. Useful Improvement Ideas

- Parse config more robustly with JSON instead of manual string search
- Add Wi-Fi reconnect logic if the connection drops later
- Add HTTP timeouts and retry strategy
- Move secrets into an example template only, not a tracked real file
- Validate ADC range and report sensor faults

The current code is good for a compact prototype, but these changes would make it safer in long-running deployments.

---

# 13. The Rest of the Project

The repository has two main parts:

- Firmware: `reference/esp8266_logger.ino`
- Backend: FastAPI app under `app/`

Other important files:

- `run.sh`: starts the backend server
- `requirements.txt`: Python dependencies
- `readings.db`: SQLite database file
- `README.md`: quick run and access instructions

So the project is not just device code. It is a complete device plus backend monitoring system.

---

# 14. Backend Entry Point

```python
app = FastAPI()
init_db()
```

From `app/main.py`, the backend:

- creates a FastAPI application
- initializes the SQLite database on startup
- exposes API routes for ingest, config, logs, and dashboard pages

This file is the traffic controller for the whole backend.

---

# 15. Running the Backend

```bash
./run.sh
```

Inside `run.sh`:

```bash
exec .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `uvicorn` runs the FastAPI app
- `app.main:app` means "load `app` from `app/main.py`"
- `--reload` restarts the server when code changes
- `0.0.0.0` allows access from other devices on the network

That network access is what lets the ESP8266 reach the backend.

---

# 16. Core API Endpoints

From `app/main.py`:

- `GET /`: health check
- `POST /ingest`: receives sensor readings
- `GET /latest`: returns newest reading
- `GET /log`: returns reading history
- `GET /device-config`: returns plain-text device settings
- `GET /dashboard`: returns the main HTML dashboard
- `GET /dashboard-data`: returns JSON used by the live dashboard

The same backend serves both machines:

- the MCU talks to API endpoints
- the browser talks to dashboard endpoints

---

# 17. How `/ingest` Works

```python
@app.post("/ingest")
def ingest(data: Reading):
    if not is_ingest_enabled():
        return {"status": "paused", "stored": fetch_readings_count()}

    reading = {
        "device_id": data.device_id,
        "voltage": data.voltage,
        "adc": data.adc,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    insert_reading(reading)
```

- FastAPI validates incoming JSON using the `Reading` model
- if logging is disabled, the backend rejects storage without crashing
- otherwise it stamps the reading with the current server time
- then it inserts the row into SQLite

So `/ingest` is the handoff point from device memory into persistent storage.

---

# 18. The Data Model

```python
class Reading(BaseModel):
    device_id: str
    voltage: float
    adc: float
```

This model in `app/models.py` defines the JSON shape expected from the ESP8266.

Why this matters:

- `device_id` identifies which device sent the data
- `voltage` is the calibrated engineering value
- `adc` keeps the raw measurement for debugging

Pydantic checks types before the backend code tries to store anything.

---

# 19. SQLite Storage Layer

```python
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    device_id TEXT NOT NULL,
    voltage REAL NOT NULL,
    adc REAL NOT NULL
)
```

In `app/db.py`, SQLite is used as a lightweight local database.

The storage layer provides functions to:

- create the table
- insert a reading
- fetch the latest reading
- fetch recent history
- count stored rows
- calculate min, max, and average voltage

This keeps database code separated from API route code.

---

# 20. Why SQLite Fits Here

SQLite is a good match for this project because:

- no separate database server is needed
- data is stored in one file: `readings.db`
- setup is almost zero
- it is enough for a small local logger

For a lab or home network project, this is simpler than running PostgreSQL or another full database service.

---

# 21. Runtime Control State

```python
ingest_enabled = True
ingest_interval_seconds = 2
```

In `app/runtime_state.py`, the backend stores two live control values:

- whether logging is enabled
- how many seconds the device should wait between posts

Helper functions such as `start_ingest()`, `stop_ingest()`, and `set_ingest_interval_seconds()` update these values.

This is temporary in-memory state, not saved in the database.

---

# 22. How `/device-config` Is Built

```python
def build_device_config_text():
    enabled_value = "1" if is_ingest_enabled() else "0"
    return f"enabled={enabled_value}\ninterval={get_ingest_interval_seconds()}\n"
```

This function in `app/dashboard.py` creates the plain-text response used by the ESP8266.

Example response:

```txt
enabled=1
interval=2
```

So the device polls the backend, and the backend answers using current runtime state.

---

# 23. Dashboard Snapshot Builder

```python
def build_dashboard_snapshot():
    latest_reading = fetch_latest_reading()
    samples_stored = fetch_readings_count()
    history = fetch_recent_readings()
    voltage_summary = fetch_voltage_summary()
```

This function collects backend data into one snapshot object for the UI.

It combines:

- newest reading
- recent chart history
- row count
- min, max, average voltage
- logging state
- device online/offline state

This is a useful pattern: build one view-model and let the UI render from that.

---

# 24. How Device Online/Offline Is Decided

```python
last_seen = datetime.strptime(latest_reading["timestamp"], "%Y-%m-%d %H:%M:%S")
age_seconds = (datetime.now() - last_seen).total_seconds()
device_online = age_seconds <= DEVICE_OFFLINE_AFTER_SECONDS
```

From `app/dashboard.py` and `app/config.py`:

- if the latest reading is recent enough, the device is considered online
- `DEVICE_OFFLINE_AFTER_SECONDS = 3`

That means the dashboard infers device health from how fresh the last sample is.

This is simple and practical for periodic telemetry systems.

---

# 25. Dashboard HTML Generation

```python
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    snapshot = build_dashboard_snapshot()
    return render_dashboard_html(snapshot, MAX_CHART_POINTS, RECENT_TABLE_ROWS)
```

The backend returns one big HTML string generated in Python.

That HTML includes:

- page structure
- CSS styling
- control buttons
- chart canvas
- JavaScript for live updates

So there is no frontend framework here. The backend directly serves the UI.

---

# 26. Dashboard Controls

The dashboard exposes control routes:

- `POST /dashboard/start`
- `POST /dashboard/stop`
- `GET /dashboard/set-interval?seconds=...`

These routes update the runtime state, then redirect back to `/dashboard`.

Meaning:

- clicking buttons in the browser changes backend state
- backend state changes what `/device-config` returns
- the device picks up those changes on its next poll

That closes the control loop.

---

# 27. Live Refresh in the Browser

```javascript
async function refreshDashboard() {
    const response = await fetch('/dashboard-data', { cache: 'no-store' });
    const data = await response.json();
    ...
}

setInterval(refreshDashboard, 1000);
```

The dashboard does not reload the whole page.

Instead it:

- fetches fresh JSON every second
- updates text values in the DOM
- redraws the chart
- updates the recent readings table

This gives a near-live view with simple client-side JavaScript.

---

# 28. Chart Rendering

The chart is drawn manually on a `<canvas>` element.

The JavaScript:

- reads recent voltage values
- calculates chart min and max
- maps values into pixel positions
- draws grid lines
- draws the voltage line and fill
- labels a few key points

This avoids extra chart libraries and keeps the project self-contained.

---

# 29. End-to-End Data Flow

1. The ESP8266 reads `A0`
2. It converts raw ADC data into voltage
3. It sends JSON to `POST /ingest`
4. FastAPI validates the payload
5. SQLite stores the reading
6. The dashboard reads data from SQLite
7. The browser fetches `/dashboard-data` every second
8. The user can change logging state or interval
9. The ESP8266 polls `/device-config` and picks up those changes

This is a full loop: sense, store, display, control, repeat.

---

# 30. Project Architecture in One Sentence

The ESP8266 is the data producer, the FastAPI app is the control and storage layer, SQLite is the persistence layer, and the dashboard is the operator interface.

---

# 31. Good Engineering Choices in This Project

- Clear separation between firmware and backend
- Small API surface with easy-to-understand routes
- Strong input validation for incoming readings
- Lightweight persistence using SQLite
- Runtime controls without reflashing the device
- Browser UI that works without a separate frontend build step

These choices keep the system easy to demo, explain, and extend.

---

# 32. Next Technical Improvements

- Persist runtime settings so they survive backend restarts
- Replace text config with JSON for safer parsing
- Add authentication if the service leaves a trusted LAN
- Add reconnect and retry logic on the ESP8266
- Store timestamps in a more explicit format, such as UTC ISO 8601
- Split dashboard HTML, CSS, and JS into separate templates or static files if the app grows

That would move the project from a compact prototype toward a more production-ready design.
