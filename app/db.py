import sqlite3

from app.config import DB_PATH, MAX_CHART_POINTS


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_id TEXT NOT NULL,
            voltage REAL NOT NULL,
            adc REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def insert_reading(reading: dict):
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO readings (timestamp, device_id, voltage, adc)
        VALUES (?, ?, ?, ?)
        """,
        (reading["timestamp"], reading["device_id"], reading["voltage"], reading["adc"]),
    )
    conn.commit()
    conn.close()


def fetch_latest_reading():
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT timestamp, device_id, voltage, adc
        FROM readings
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def fetch_recent_readings(limit=MAX_CHART_POINTS):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT timestamp, device_id, voltage, adc
        FROM readings
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]


def fetch_readings_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    conn.close()
    return count


def fetch_voltage_summary():
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT
            MIN(voltage) AS min_voltage,
            MAX(voltage) AS max_voltage,
            AVG(voltage) AS avg_voltage
        FROM readings
        """
    ).fetchone()
    conn.close()

    if row is None or row["min_voltage"] is None:
        return {
            "min_voltage": None,
            "max_voltage": None,
            "avg_voltage": None,
        }

    return {
        "min_voltage": row["min_voltage"],
        "max_voltage": row["max_voltage"],
        "avg_voltage": row["avg_voltage"],
    }

