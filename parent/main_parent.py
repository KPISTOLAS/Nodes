"""
main_parent.py - Κύριο πρόγραμμα Γονικού Κόμβου (Parent Node / LoRa Gateway)
--------------------------------------------------------------------------------
Ρόλος στην αρχιτεκτονική:
  1. Λειτουργεί ως πύλη LoRa (LoRa gateway) - λαμβάνει δεδομένα από
     θυγατρικούς κόμβους (C1..CN).
  2. Προεπεξεργάζεται, φιλτράρει και επικυρώνει τα δεδομένα.
  3. Τα αποθηκεύει προσωρινά (buffering) σε ελαφριά τοπική βάση (SQLite).
  4. Μέσω Wi-Fi, συγχρονίζει (upload) τα δεδομένα στο Supabase (cloud).

Χρήση:
  python3 main_parent.py
"""

import json
import logging
import sys
import time

from raspi_lora import LoRa, ModemConfig

import config
import local_db
from supabase_sync import SupabaseSync

logging.basicConfig(
    filename=config.LOG_FILE,
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("main_parent")
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
logger.addHandler(console)


def validate_payload(payload: dict) -> bool:
    """Επικυρώνει ότι το πακέτο περιέχει τα απαραίτητα πεδία και ότι οι
    τιμές βρίσκονται εντός λογικών ορίων (φιλτράρισμα θορύβου/σφαλμάτων)."""
    for field in config.REQUIRED_FIELDS:
        if field not in payload or payload[field] is None:
            logger.warning(f"Απόρριψη πακέτου - λείπει πεδίο '{field}': {payload}")
            return False

    for field, (min_v, max_v) in config.VALID_RANGES.items():
        value = payload.get(field)
        if value is not None and not (min_v <= value <= max_v):
            logger.warning(
                f"Απόρριψη πακέτου - τιμή '{field}'={value} εκτός ορίων "
                f"[{min_v}, {max_v}]: {payload}"
            )
            return False

    return True


class ParentNodeGateway:
    def __init__(self):
        local_db.init_db()

        self.lora = LoRa(
            spi_channel=config.LORA_SPI_CHANNEL,
            interrupt_pin=config.LORA_INTERRUPT_PIN,
            reset_pin=config.LORA_RESET_PIN,
            freq=config.LORA_FREQUENCY,
            tx_power=config.LORA_TX_POWER,
            modem_config=ModemConfig.Bw125Cr45Sf128,
            acks=True,  # Στέλνει αυτόματα ACK πίσω στον θυγατρικό κόμβο
        )
        self.lora.on_recv = self._on_receive

        self.sync_service = SupabaseSync()

        logger.info(f"Γονικός κόμβος {config.NODE_ID} (LoRa gateway) αρχικοποιήθηκε.")

    def _on_receive(self, message):
        """Callback που καλείται αυτόματα όταν φτάνει πακέτο LoRa."""
        try:
            raw = bytes(message.data).decode("utf-8")
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.warning(f"Λήψη μη έγκυρου (corrupt) πακέτου: {e}")
            return

        logger.info(f"Λήφθηκε πακέτο από κόμβο '{payload.get('node_id')}': {payload}")

        if not validate_payload(payload):
            return  # φιλτράρισμα - απορρίπτεται εκτός εύρους/ελλιπές

        inserted = local_db.insert_reading(payload)
        if inserted:
            logger.info(f"Αποθηκεύτηκε τοπικά (buffer) η μέτρηση από {payload['node_id']}.")
        else:
            logger.debug("Η μέτρηση απορρίφθηκε ως διπλότυπη (dedup).")

    def run_forever(self):
        self.sync_service.start()
        logger.info("Ο γονικός κόμβος είναι σε λειτουργία - αναμονή δεδομένων LoRa...")
        try:
            while True:
                time.sleep(1)  # Το raspi_lora ακούει ασύγχρονα μέσω interrupt
        except KeyboardInterrupt:
            logger.info("Τερματισμός από χρήστη (Ctrl+C).")
        finally:
            self.sync_service.stop()


if __name__ == "__main__":
    gateway = ParentNodeGateway()
    gateway.run_forever()
