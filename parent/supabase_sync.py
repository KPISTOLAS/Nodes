"""
supabase_sync.py - Συγχρονισμός τοπικής βάσης με το Supabase (Cloud)
------------------------------------------------------------------------
Ρόλος στην αρχιτεκτονική: Wi-Fi σύνδεση Γονικού Κόμβου -> Cloud, με υψηλό
εύρος ζώνης για γρήγορη μεταφορά των buffered δεδομένων στον κεντρικό
διακομιστή (Supabase).
"""

import logging
import time
import threading

from supabase import create_client, Client

import config
import local_db

logger = logging.getLogger("supabase_sync")


class SupabaseSync:
    def __init__(self):
        self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        self._stop_event = threading.Event()
        self._thread = None

    def _row_to_supabase_record(self, row: dict) -> dict:
        return {
            "node_id": row["node_id"],
            "parent_id": row["parent_id"],
            "timestamp": row["timestamp"],
            "temperature_c": row["temperature_c"],
            "humidity_pct": row["humidity_pct"],
            "wind_speed_ms": row["wind_speed_ms"],
            "soil_moisture_pct": row["soil_moisture_pct"],
            "battery_voltage_v": row["battery_voltage_v"],
            "received_at": row["received_at"],
        }

    def sync_once(self) -> int:
        """Στέλνει ένα batch ανεπίδοτων εγγραφών στο Supabase.
        Επιστρέφει τον αριθμό των εγγραφών που συγχρονίστηκαν επιτυχώς."""
        rows = local_db.fetch_unsynced(limit=config.SYNC_BATCH_SIZE)
        if not rows:
            return 0

        records = [self._row_to_supabase_record(r) for r in rows]

        for attempt in range(1, config.SYNC_MAX_RETRIES + 1):
            try:
                # upsert με βάση (node_id, timestamp) αποτρέπει διπλότυπα και
                # στο ίδιο το cloud, σε περίπτωση επανάληψης αποστολής.
                self.client.table(config.SUPABASE_TABLE) \
                    .upsert(records, on_conflict="node_id,timestamp") \
                    .execute()

                synced_ids = [r["id"] for r in rows]
                local_db.mark_synced(synced_ids)
                logger.info(f"Συγχρονίστηκαν {len(synced_ids)} εγγραφές με το Supabase.")
                return len(synced_ids)

            except Exception as e:
                logger.warning(
                    f"Αποτυχία συγχρονισμού (προσπάθεια {attempt}/{config.SYNC_MAX_RETRIES}): {e}"
                )
                time.sleep(2 ** attempt)  # exponential backoff

        logger.error("Οριστική αποτυχία συγχρονισμού batch - θα ξαναδοκιμαστεί αργότερα.")
        return 0

    def _run_loop(self):
        logger.info("Εκκίνηση background thread συγχρονισμού με Supabase.")
        while not self._stop_event.is_set():
            try:
                self.sync_once()
            except Exception as e:
                logger.error(f"Απρόσμενο σφάλμα στο sync loop: {e}")
            self._stop_event.wait(config.SYNC_INTERVAL_S)

    def start(self):
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
