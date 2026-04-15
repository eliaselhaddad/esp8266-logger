# ESP8266 Logger Backend

FastAPI backend and ESP8266 sketch for logging voltage readings into a local SQLite database.

## Setup

Create a Python virtual environment and install the backend dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run Locally

```bash
./run.sh
```

## ESP8266 sketch secrets

Sensitive device settings live in `reference/esp8266_secrets.h`.

Use `reference/esp8266_secrets.example.h` as the template you can share or commit.

```bash
cp reference/esp8266_secrets.example.h reference/esp8266_secrets.h
```

Then edit `reference/esp8266_secrets.h` with your Wi-Fi name, password, backend host, backend port, and device ID.

The real `reference/esp8266_secrets.h` file is ignored by Git and should not be committed.

## Free port 8000 if needed

```bash
fuser -k 8000/tcp
```

## Access in browser

[http://localhost:8000/dashboard](http://localhost:8000/dashboard)

## Access from network (ESP8266 / phone)

```text
http://YOUR_COMPUTER_IP:8000/dashboard
```

Replace `YOUR_COMPUTER_IP` with the IP address of the computer running the backend.
