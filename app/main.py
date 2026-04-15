from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import MAX_CHART_POINTS, RECENT_TABLE_ROWS
from app.dashboard import (
    build_dashboard_snapshot,
    build_device_config_text,
    render_dashboard_html,
)
from app.db import fetch_latest_reading, fetch_readings_count, fetch_recent_readings, init_db, insert_reading
from app.models import Reading
from app.runtime_state import (
    get_ingest_interval_seconds,
    is_ingest_enabled,
    set_ingest_interval_seconds,
    start_ingest,
    stop_ingest,
)

app = FastAPI()
init_db()


@app.get("/")
def root():
    return {"message": "backend alive"}


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
    return {"status": "ok", "stored": fetch_readings_count()}


@app.get("/latest")
def latest():
    latest_reading = fetch_latest_reading()
    if latest_reading is None:
        return {"message": "no readings yet"}
    return latest_reading


@app.get("/log")
def log():
    return fetch_recent_readings(limit=1000)


@app.get("/device-config")
def device_config():
    return HTMLResponse(content=build_device_config_text(), media_type="text/plain")


@app.get("/dashboard-data")
def dashboard_data():
    return build_dashboard_snapshot()


@app.post("/dashboard/start")
def dashboard_start():
    start_ingest()
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/dashboard/stop")
def dashboard_stop():
    stop_ingest()
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard/set-interval")
def set_interval(seconds: int):
    set_ingest_interval_seconds(seconds)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    snapshot = build_dashboard_snapshot()
    return render_dashboard_html(snapshot, MAX_CHART_POINTS, RECENT_TABLE_ROWS)
