# Agent Notes

This repository contains a FastAPI backend plus an ESP8266 Arduino sketch for logging voltage readings into SQLite.

## Project Layout

- `app/main.py`: FastAPI routes, including `/ingest`, `/dashboard`, `/latest`, and `/log`.
- `app/db.py`: SQLite connection, schema creation, inserts, and read queries.
- `app/models.py`: Pydantic request model for MCU readings.
- `app/dashboard.py`: Dashboard HTML/CSS/JavaScript rendering.
- `app/runtime_state.py`: In-memory logging control state.
- `reference/esp8266_logger.ino`: ESP8266 sketch that reads `A0` and posts JSON to `/ingest`.
- `reference/esp8266_secrets.example.h`: Safe template for Wi-Fi/backend settings.

## Local Setup

Use the existing virtual environment if present:

```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

If dependencies need to be installed:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Validation

Run this before committing Python changes:

```bash
.venv/bin/python -m py_compile app/*.py
```

If the dashboard UI changes, start the server and inspect:

```text
http://localhost:8000/dashboard
```

## Git Hygiene

Do not commit local secrets or runtime artifacts:

- `reference/esp8266_secrets.h`
- `readings.db`
- `.venv/`
- `__pycache__/`
- `.playwright-libs/`

The real secrets file should be created locally from:

```bash
cp reference/esp8266_secrets.example.h reference/esp8266_secrets.h
```

## Data Flow

The ESP8266 posts JSON to `POST /ingest` with:

```json
{
  "device_id": "esp8266-1",
  "voltage": 1.592,
  "adc": 552.0
}
```

FastAPI validates this with `Reading`, adds a server timestamp, and stores it in the `readings` table inside `readings.db`.
