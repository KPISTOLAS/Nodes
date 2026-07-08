"""
local_db.py - Ελαφριά τοπική βάση δεδομένων (SQLite) για buffering
-----------------------------------------------------------------------
Ρόλος: τοπική προσωρινή αποθήκευση δεδομένων στον Γονικό Κόμβο πριν/κατά
τη μεταφορά τους στο cloud (Supabase), και μείωση πλεονασμού (dedup).
"""

import sqlite3
import logging
import time
from contextlib import contextmanager

import config

logger = logging.getLogger("local_db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    parent_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    temperature_c REAL,
    humidity_pct REAL,
    wind_speed_ms REAL,
    soil_moisture_pct REAL,
    battery_voltage_v REAL,
    received_at REAL NOT NULL,
    synced INTEGER NOT NULL DEFAULT 0,
    UNIQUE(node_id, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_synced ON sensor_data(synced);
"""


@contextmanager
def get_connection():
    conn = sqlite3.connect(config.LOCAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)
    logger.info(f"Τοπική βάση δεδομένων έτοιμη: {config.LOCAL_DB_PATH}")


def is_duplicate(node_id: str, timestamp: float) -> bool:
    """Ελέγχει αν υπάρχει ήδη πολύ κοντινή εγγραφή (ίδιο node, κοντινό timestamp),
    ώστε να μειωθεί ο πλεονασμός (π.χ. λόγω retransmission στο LoRa)."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT timestamp FROM sensor_data WHERE node_id = ? "
            "AND ABS(timestamp - ?) < ? LIMIT 1",
            (node_id, timestamp, config.DEDUP_WINDOW_S),
        )
        return cur.fetchone() is not None


def insert_reading(payload: dict) -> bool:
    """Εισάγει μια επικυρωμένη μέτρηση στην τοπική βάση.
    Επιστρέφει False αν είναι διπλότυπη ή αποτύχει."""
    if is_duplicate(payload["node_id"], payload["timestamp"]):
        logger.debug(f"Παράλειψη διπλότυπης εγγραφής από {payload['node_id']}")
        return False

    try:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO sensor_data
                   (node_id, parent_id, timestamp, temperature_c, humidity_pct,
                    wind_speed_ms, soil_moisture_pct, battery_voltage_v,
                    received_at, synced)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (
                    payload["node_id"],
                    config.NODE_ID,
                    payload["timestamp"],
                    payload.get("temperature_c"),
                    payload.get("humidity_pct"),
                    payload.get("wind_speed_ms"),
                    payload.get("soil_moisture_pct"),
                    payload.get("battery_voltage_v"),
                    time.time(),
                ),
            )
        return True
    except sqlite3.IntegrityError:
        logger.debug("IntegrityError - πιθανό διπλότυπο (UNIQUE constraint).")
        return False


def fetch_unsynced(limit: int = 50):
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM sensor_data WHERE synced = 0 ORDER BY id ASC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def mark_synced(ids: list):
    if not ids:
        return
    with get_connection() as conn:
        placeholders = ",".join("?" for _ in ids)
        conn.execute(
            f"UPDATE sensor_data SET synced = 1 WHERE id IN ({placeholders})", ids
        )


def purge_synced_older_than(seconds: float):
    """Προαιρετικός καθαρισμός παλιών, ήδη συγχρονισμένων εγγραφών ώστε
    η τοπική βάση να μην μεγαλώνει επ' αόριστον."""
    cutoff = time.time() - seconds
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM sensor_data WHERE synced = 1 AND received_at < ?",
            (cutoff,),
        )
