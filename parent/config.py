"""
config.py - Ρυθμίσεις Γονικού Κόμβου (Parent Node / LoRa Gateway)
--------------------------------------------------------------------
"""

# ---------- Ταυτότητα κόμβου ----------
NODE_ID = "P1"

# ---------- LoRa (SPI - RFM95/SX1276) ----------
LORA_FREQUENCY = 868.0
LORA_SPI_CHANNEL = 0
LORA_INTERRUPT_PIN = 24
LORA_RESET_PIN = 25
LORA_TX_POWER = 14
LORA_GATEWAY_ADDRESS = 1        # Η διεύθυνση LoRa του ίδιου του gateway

# ---------- Επικύρωση / Φιλτράρισμα δεδομένων ----------
VALID_RANGES = {
    "temperature_c": (-30.0, 60.0),
    "humidity_pct": (0.0, 100.0),
    "wind_speed_ms": (0.0, 60.0),
    "soil_moisture_pct": (0.0, 100.0),
    "battery_voltage_v": (2.5, 4.5),
}
REQUIRED_FIELDS = ["node_id", "timestamp", "temperature_c", "humidity_pct",
                   "wind_speed_ms", "soil_moisture_pct"]

# ---------- Τοπική βάση δεδομένων (buffering) ----------
LOCAL_DB_PATH = "edge_buffer.db"
DEDUP_WINDOW_S = 5.0            # Παράθυρο θεώρησης "διπλότυπου" μηνύματος

# ---------- Wi-Fi / Supabase Sync ----------
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"     # <-- ΣΥΜΠΛΗΡΩΣΕ
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_OR_ANON_KEY"    # <-- ΣΥΜΠΛΗΡΩΣΕ
SUPABASE_TABLE = "sensor_readings"

SYNC_INTERVAL_S = 30            # Πόσο συχνά ελέγχει για νέα δεδομένα προς αποστολή
SYNC_BATCH_SIZE = 50            # Πόσες εγγραφές στέλνει ανά batch
SYNC_MAX_RETRIES = 3

# ---------- Logging ----------
LOG_FILE = "parent_node.log"
LOG_LEVEL = "INFO"
