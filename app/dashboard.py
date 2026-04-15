from datetime import datetime

from app.config import DEVICE_OFFLINE_AFTER_SECONDS, RECENT_TABLE_ROWS
from app.db import (
    fetch_latest_reading,
    fetch_readings_count,
    fetch_recent_readings,
    fetch_voltage_summary,
)
from app.runtime_state import get_ingest_interval_seconds, is_ingest_enabled


def build_device_config_text():
    enabled_value = "1" if is_ingest_enabled() else "0"
    return f"enabled={enabled_value}\ninterval={get_ingest_interval_seconds()}\n"


def build_dashboard_snapshot():
    latest_reading = fetch_latest_reading()
    samples_stored = fetch_readings_count()
    history = fetch_recent_readings()
    recent_rows = fetch_recent_readings(limit=RECENT_TABLE_ROWS)
    voltage_summary = fetch_voltage_summary()

    if latest_reading is None:
        reading = {
            "voltage": "--",
            "adc": "--",
            "device_id": "--",
            "timestamp": "--",
        }
        last_seen_seconds = None
        device_online = False
    else:
        reading = latest_reading
        last_seen = datetime.strptime(latest_reading["timestamp"], "%Y-%m-%d %H:%M:%S")
        age_seconds = (datetime.now() - last_seen).total_seconds()
        last_seen_seconds = int(age_seconds)
        device_online = age_seconds <= DEVICE_OFFLINE_AFTER_SECONDS

    return {
        "reading": reading,
        "ingest_enabled": is_ingest_enabled(),
        "ingest_interval_seconds": get_ingest_interval_seconds(),
        "device_online": device_online,
        "last_seen_seconds": last_seen_seconds,
        "samples_stored": samples_stored,
        "history": history,
        "recent_rows": recent_rows,
        "voltage_summary": voltage_summary,
    }


def render_dashboard_html(snapshot: dict, max_chart_points: int, recent_table_rows: int):
    reading = snapshot["reading"]
    voltage = reading["voltage"]
    adc = reading["adc"]
    device_id = reading["device_id"]
    timestamp = reading["timestamp"]
    samples_stored = snapshot["samples_stored"]
    voltage_summary = snapshot["voltage_summary"]

    if snapshot["last_seen_seconds"] is None:
        last_seen_text = "--"
    else:
        last_seen_text = f'{snapshot["last_seen_seconds"]} sec ago'

    if snapshot["ingest_enabled"]:
        status_text = "Running"
        status_class = "status running"
        action_path = "/dashboard/stop"
        button_label = "Stop Logging"
        button_class = "button stop"
    else:
        status_text = "Stopped"
        status_class = "status stopped"
        action_path = "/dashboard/start"
        button_label = "Start Logging"
        button_class = "button start"

    if snapshot["device_online"]:
        device_status_text = "Device Online"
        device_status_class = "status running"
    else:
        device_status_text = "Device Offline"
        device_status_class = "status stopped"

    if voltage_summary["min_voltage"] is None:
        min_voltage = "--"
        max_voltage = "--"
        avg_voltage = "--"
    else:
        min_voltage = f'{voltage_summary["min_voltage"]:.3f}'
        max_voltage = f'{voltage_summary["max_voltage"]:.3f}'
        avg_voltage = f'{voltage_summary["avg_voltage"]:.3f}'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ESP8266 Dashboard</title>
        <style>
            :root {{
                --bg-top: #f7efe4;
                --bg-bottom: #d9ebff;
                --card: rgba(255, 255, 255, 0.82);
                --text: #172033;
                --muted: #5f6c85;
                --line: rgba(23, 32, 51, 0.08);
                --shadow: 0 22px 60px rgba(33, 53, 85, 0.16);
                --green-bg: #d8f5e4;
                --green-text: #166534;
                --red-bg: #fde2e2;
                --red-text: #991b1b;
                --blue-dark: #1d4ed8;
                --chart-line: #0f766e;
                --chart-fill: rgba(15, 118, 110, 0.14);
            }}
            body {{
                align-items: center;
                background:
                    radial-gradient(circle at top left, rgba(255,255,255,0.85), transparent 30%),
                    linear-gradient(160deg, var(--bg-top), var(--bg-bottom));
                color: var(--text);
                display: flex;
                font-family: "Trebuchet MS", "Segoe UI", sans-serif;
                justify-content: center;
                margin: 0;
                min-height: 100vh;
                padding: 24px;
            }}
            .card {{
                backdrop-filter: blur(12px);
                background: var(--card);
                border: 1px solid rgba(255, 255, 255, 0.7);
                border-radius: 28px;
                box-shadow: var(--shadow);
                max-width: 980px;
                padding: 32px;
                width: 100%;
            }}
            .header {{
                align-items: start;
                display: flex;
                gap: 16px;
                justify-content: space-between;
                margin-bottom: 24px;
            }}
            h1 {{
                font-size: 34px;
                margin: 0;
            }}
            .subtitle {{
                color: var(--muted);
                margin-top: 8px;
            }}
            .small {{
                color: var(--muted);
            }}
            .status {{
                display: inline-block;
                padding: 10px 14px;
                border-radius: 999px;
                font-weight: bold;
            }}
            .running {{
                background: var(--green-bg);
                color: var(--green-text);
            }}
            .stopped {{
                background: var(--red-bg);
                color: var(--red-text);
            }}
            .pill-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                justify-content: flex-end;
            }}
            .layout {{
                display: grid;
                gap: 22px;
                grid-template-columns: 1.1fr 0.9fr;
            }}
            .panel {{
                background: rgba(255, 255, 255, 0.64);
                border: 1px solid var(--line);
                border-radius: 22px;
                padding: 22px;
            }}
            .hero {{
                align-items: end;
                display: flex;
                justify-content: space-between;
                margin-bottom: 18px;
            }}
            .hero-value {{
                font-size: 64px;
                font-weight: 700;
                line-height: 1;
                margin: 0;
            }}
            .hero-unit {{
                color: var(--muted);
                font-size: 18px;
                margin-left: 8px;
            }}
            .stats-grid {{
                display: grid;
                gap: 14px;
                grid-template-columns: repeat(3, 1fr);
                margin-bottom: 22px;
            }}
            .stat {{
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 16px;
            }}
            .stat-label {{
                color: var(--muted);
                font-size: 13px;
                margin-bottom: 8px;
                text-transform: uppercase;
            }}
            .stat-value {{
                font-size: 24px;
                font-weight: 700;
            }}
            .chart-title {{
                align-items: baseline;
                display: flex;
                justify-content: space-between;
                margin-bottom: 14px;
            }}
            .chart-wrap {{
                background: linear-gradient(180deg, rgba(255,255,255,0.75), rgba(235,245,255,0.75));
                border: 1px solid var(--line);
                border-radius: 20px;
                padding: 14px;
            }}
            canvas {{
                display: block;
                height: 280px;
                width: 100%;
            }}
            .button {{
                border: none;
                border-radius: 14px;
                color: white;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                padding: 14px 18px;
            }}
            .start {{
                background: #15803d;
            }}
            .stop {{
                background: #b91c1c;
            }}
            .slider-wrap {{
                text-align: left;
            }}
            .slider-label {{
                display: block;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .slider-value {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .slider {{
                width: 100%;
            }}
            .apply {{
                background: var(--blue-dark);
                margin-top: 14px;
                width: 100%;
            }}
            .actions {{
                display: grid;
                gap: 14px;
                margin-top: 18px;
            }}
            .hint {{
                color: var(--muted);
                font-size: 14px;
                margin-top: 10px;
            }}
            .table-panel {{
                margin-top: 22px;
            }}
            .summary-grid {{
                display: grid;
                gap: 14px;
                grid-template-columns: repeat(3, 1fr);
                margin-top: 22px;
            }}
            .table-wrap {{
                border: 1px solid var(--line);
                border-radius: 20px;
                overflow: hidden;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
            }}
            th, td {{
                border-bottom: 1px solid var(--line);
                font-size: 14px;
                padding: 12px 14px;
                text-align: left;
            }}
            th {{
                background: rgba(255, 255, 255, 0.78);
                color: var(--muted);
                font-size: 12px;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }}
            tr:last-child td {{
                border-bottom: none;
            }}
            .empty-row {{
                color: var(--muted);
                text-align: center;
            }}
            @media (max-width: 860px) {{
                .layout {{
                    grid-template-columns: 1fr;
                }}
                .stats-grid {{
                    grid-template-columns: 1fr;
                }}
                .header, .hero {{
                    display: block;
                }}
                .pill-row {{
                    justify-content: flex-start;
                    margin-top: 16px;
                }}
                .hero-value {{
                    font-size: 52px;
                    margin-top: 14px;
                }}
                .card {{
                    padding: 22px;
                }}
                .summary-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <div>
                    <h1>ESP8266 Dashboard</h1>
                    <div class="subtitle">Live voltage monitoring with local device controls</div>
                </div>
                <div class="pill-row">
                    <div class="{status_class}" id="status-pill">Logging {status_text}</div>
                    <div class="{device_status_class}" id="device-status-pill">{device_status_text}</div>
                </div>
            </div>

            <div class="layout">
                <div class="panel">
                    <div class="hero">
                        <div>
                            <div class="small">Current voltage</div>
                            <div class="hero-value"><span id="voltage">{voltage}</span><span class="hero-unit">V</span></div>
                        </div>
                        <div class="small">Updated <span id="timestamp">{timestamp}</span></div>
                    </div>

                    <div class="stats-grid">
                        <div class="stat">
                            <div class="stat-label">ADC</div>
                            <div class="stat-value" id="adc">{adc}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Device</div>
                            <div class="stat-value" id="device-id">{device_id}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Interval</div>
                            <div class="stat-value"><span id="interval-readout">{snapshot["ingest_interval_seconds"]}</span> sec</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Last Seen</div>
                            <div class="stat-value" id="last-seen">{last_seen_text}</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Samples Stored</div>
                            <div class="stat-value" id="samples-stored">{samples_stored}</div>
                        </div>
                    </div>

                    <div class="chart-title">
                        <strong>Recent voltage history</strong>
                        <span class="small">Last {max_chart_points} samples</span>
                    </div>
                    <div class="chart-wrap">
                        <canvas id="voltage-chart" width="640" height="280"></canvas>
                    </div>
                    <div class="hint">The chart updates every 1 second without reloading the page.</div>

                    <div class="summary-grid">
                        <div class="stat">
                            <div class="stat-label">Min Voltage</div>
                            <div class="stat-value"><span id="min-voltage">{min_voltage}</span> V</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Max Voltage</div>
                            <div class="stat-value"><span id="max-voltage">{max_voltage}</span> V</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">Average Voltage</div>
                            <div class="stat-value"><span id="avg-voltage">{avg_voltage}</span> V</div>
                            <div class="small" id="avg-samples-note">over {samples_stored} samples</div>
                        </div>
                    </div>
                </div>

                <div class="panel">
                    <strong>Controls</strong>
                    <div class="actions">
                        <form id="toggle-form" method="post" action="{action_path}">
                            <button class="{button_class}" id="toggle-button" type="submit">{button_label}</button>
                        </form>
                        <form class="slider-wrap" method="get" action="/dashboard/set-interval">
                            <label class="slider-label" for="seconds">Logging interval</label>
                            <div class="slider-value"><span id="seconds-value">{snapshot["ingest_interval_seconds"]}</span> sec</div>
                            <input
                                class="slider"
                                id="seconds"
                                max="60"
                                min="1"
                                name="seconds"
                                oninput="document.getElementById('seconds-value').textContent = this.value"
                                type="range"
                                value="{snapshot["ingest_interval_seconds"]}"
                            >
                            <button class="button apply" type="submit">Apply Interval</button>
                        </form>
                    </div>
                </div>
            </div>

            <div class="panel table-panel">
                <div class="chart-title">
                    <strong>Recent readings</strong>
                    <span class="small">Latest {recent_table_rows} rows from SQLite</span>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Device</th>
                                <th>Voltage</th>
                                <th>ADC</th>
                            </tr>
                        </thead>
                        <tbody id="recent-readings-body">
                            <tr>
                                <td class="empty-row" colspan="4">No readings yet</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <script>
            function renderRecentRows(rows) {{
                const tbody = document.getElementById('recent-readings-body');

                if (!rows.length) {{
                    tbody.innerHTML = `
                        <tr>
                            <td class="empty-row" colspan="4">No readings yet</td>
                        </tr>
                    `;
                    return;
                }}

                const sortedRows = [...rows].reverse();
                tbody.innerHTML = sortedRows.map((row) => `
                    <tr>
                        <td>${{row.timestamp}}</td>
                        <td>${{row.device_id}}</td>
                        <td>${{Number(row.voltage).toFixed(3)}} V</td>
                        <td>${{Number(row.adc).toFixed(1)}}</td>
                    </tr>
                `).join('');
            }}

            function drawChart(history) {{
                const canvas = document.getElementById('voltage-chart');
                const ctx = canvas.getContext('2d');
                const width = canvas.width;
                const height = canvas.height;
                const paddingLeft = 58;
                const paddingRight = 20;
                const paddingTop = 20;
                const paddingBottom = 34;

                ctx.clearRect(0, 0, width, height);

                const chartWidth = width - paddingLeft - paddingRight;
                const chartHeight = height - paddingTop - paddingBottom;

                ctx.strokeStyle = 'rgba(23, 32, 51, 0.10)';
                ctx.lineWidth = 1;
                ctx.fillStyle = '#5f6c85';
                ctx.font = '12px Trebuchet MS';
                ctx.textAlign = 'right';
                ctx.textBaseline = 'middle';

                for (let i = 0; i < 4; i++) {{
                    const y = paddingTop + (chartHeight / 3) * i;
                    ctx.beginPath();
                    ctx.moveTo(paddingLeft, y);
                    ctx.lineTo(width - paddingRight, y);
                    ctx.stroke();
                }}

                if (!history.length) {{
                    ctx.fillStyle = '#5f6c85';
                    ctx.font = '16px Trebuchet MS';
                    ctx.textAlign = 'left';
                    ctx.fillText('No readings yet', paddingLeft, height / 2);
                    return;
                }}

                const points = history.map((item) => Number(item.voltage));
                const minVoltage = Math.min(...points);
                const maxVoltage = Math.max(...points);
                const range = Math.max(maxVoltage - minVoltage, 0.2);
                const chartMin = Math.max(0, minVoltage - range * 0.15);
                const chartMax = maxVoltage + range * 0.15;
                const chartRange = Math.max(chartMax - chartMin, 0.2);

                for (let i = 0; i < 4; i++) {{
                    const value = chartMax - (chartRange / 3) * i;
                    const y = paddingTop + (chartHeight / 3) * i;
                    ctx.fillText(`${{value.toFixed(2)}} V`, paddingLeft - 8, y);
                }}

                const xStep = history.length > 1 ? chartWidth / (history.length - 1) : 0;
                const pointPositions = [];

                ctx.beginPath();
                history.forEach((item, index) => {{
                    const x = paddingLeft + xStep * index;
                    const normalized = (Number(item.voltage) - chartMin) / chartRange;
                    const y = height - paddingBottom - normalized * chartHeight;
                    pointPositions.push({{ x, y, voltage: Number(item.voltage) }});
                    if (index === 0) {{
                        ctx.moveTo(x, y);
                    }} else {{
                        ctx.lineTo(x, y);
                    }}
                }});

                ctx.lineWidth = 3;
                ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--chart-line');
                ctx.stroke();

                ctx.lineTo(width - paddingRight, height - paddingBottom);
                ctx.lineTo(paddingLeft, height - paddingBottom);
                ctx.closePath();
                ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--chart-fill');
                ctx.fill();

                ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--chart-line');
                pointPositions.forEach((point) => {{
                    ctx.beginPath();
                    ctx.arc(point.x, point.y, 3.5, 0, Math.PI * 2);
                    ctx.fill();
                }});

                ctx.fillStyle = '#172033';
                ctx.font = '11px Trebuchet MS';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';

                const labelIndices = new Set([0, history.length - 1, Math.floor((history.length - 1) / 2)]);
                labelIndices.forEach((index) => {{
                    const point = pointPositions[index];
                    if (!point) return;
                    ctx.fillText(`${{point.voltage.toFixed(2)}}V`, point.x, point.y - 8);
                }});
            }}

            async function refreshDashboard() {{
                try {{
                    const response = await fetch('/dashboard-data', {{ cache: 'no-store' }});
                    if (!response.ok) return;

                    const data = await response.json();
                    const reading = data.reading;

                    document.getElementById('voltage').textContent = reading.voltage;
                    document.getElementById('adc').textContent = reading.adc;
                    document.getElementById('device-id').textContent = reading.device_id;
                    document.getElementById('timestamp').textContent = reading.timestamp;
                    document.getElementById('interval-readout').textContent = data.ingest_interval_seconds;
                    document.getElementById('samples-stored').textContent = data.samples_stored;

                    if (data.last_seen_seconds === null) {{
                        document.getElementById('last-seen').textContent = '--';
                    }} else {{
                        document.getElementById('last-seen').textContent = `${{data.last_seen_seconds}} sec ago`;
                    }}

                    if (data.voltage_summary.min_voltage === null) {{
                        document.getElementById('min-voltage').textContent = '--';
                        document.getElementById('max-voltage').textContent = '--';
                        document.getElementById('avg-voltage').textContent = '--';
                        document.getElementById('avg-samples-note').textContent = 'over 0 samples';
                    }} else {{
                        document.getElementById('min-voltage').textContent = Number(data.voltage_summary.min_voltage).toFixed(3);
                        document.getElementById('max-voltage').textContent = Number(data.voltage_summary.max_voltage).toFixed(3);
                        document.getElementById('avg-voltage').textContent = Number(data.voltage_summary.avg_voltage).toFixed(3);
                        document.getElementById('avg-samples-note').textContent = `over ${{data.samples_stored}} samples`;
                    }}

                    const statusPill = document.getElementById('status-pill');
                    const deviceStatusPill = document.getElementById('device-status-pill');
                    const toggleForm = document.getElementById('toggle-form');
                    const toggleButton = document.getElementById('toggle-button');

                    if (data.ingest_enabled) {{
                        statusPill.textContent = 'Logging Running';
                        statusPill.className = 'status running';
                        toggleForm.action = '/dashboard/stop';
                        toggleButton.textContent = 'Stop Logging';
                        toggleButton.className = 'button stop';
                    }} else {{
                        statusPill.textContent = 'Logging Stopped';
                        statusPill.className = 'status stopped';
                        toggleForm.action = '/dashboard/start';
                        toggleButton.textContent = 'Start Logging';
                        toggleButton.className = 'button start';
                    }}

                    if (data.device_online) {{
                        deviceStatusPill.textContent = 'Device Online';
                        deviceStatusPill.className = 'status running';
                    }} else {{
                        deviceStatusPill.textContent = 'Device Offline';
                        deviceStatusPill.className = 'status stopped';
                    }}

                    drawChart(data.history);
                    renderRecentRows(data.recent_rows);
                }} catch (error) {{
                    console.error('Dashboard refresh failed', error);
                }}
            }}

            refreshDashboard();
            setInterval(refreshDashboard, 1000);
        </script>
    </body>
    </html>
    """

