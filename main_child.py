"""
main_child.py - Κύριο πρόγραμμα Θυγατρικού Κόμβου (Child Node)
------------------------------------------------------------------
Ρόλος στην αρχιτεκτονική:
  Συλλέγει τοπικά δεδομένα (θερμοκρασία, υγρασία αέρα, άνεμος, υγρασία
  εδάφους) σε τακτικά χρονικά διαστήματα και τα αποστέλλει στον Γονικό
  Κόμβο (Parent Node) μέσω LoRa (μεγάλης εμβέλειας, χαμηλής κατανάλωσης).

Χρήση:
  python3 main_child.py
"""

import json
import logging
import time
import sys

from raspi_lora import LoRa, ModemConfig

import config
import sensors

logging.basicConfig(
    filename=config.LOG_FILE,
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("main_child")
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
logger.addHandler(console)


class ChildNode:
    def __init__(self):
        self.lora = LoRa(
            spi_channel=config.LORA_SPI_CHANNEL,
            interrupt_pin=config.LORA_INTERRUPT_PIN,
            reset_pin=config.LORA_RESET_PIN,
            freq=config.LORA_FREQUENCY,
            tx_power=config.LORA_TX_POWER,
            modem_config=ModemConfig.Bw125Cr45Sf128,
        )
        self.parent_address = self._resolve_parent_address()
        logger.info(f"Θυγατρικός κόμβος {config.NODE_ID} αρχικοποιήθηκε. "
                    f"Γονικός κόμβος στόχος: {config.PARENT_NODE_ID}")

    @staticmethod
    def _resolve_parent_address():
        # Στην πράξη η διεύθυνση LoRa (0-255) μπορεί να αντιστοιχιστεί
        # σε πίνακα node_id -> lora_address. Εδώ απλοποιείται σε 1.
        return 1

    def send_reading(self, payload: dict) -> bool:
        """Στέλνει ένα πακέτο δεδομένων στον γονικό κόμβο με αναμονή ACK
        και επαναπροσπάθειες, ώστε να μειωθεί η απώλεια πακέτων."""
        message = json.dumps(payload).encode("utf-8")

        for attempt in range(1, config.LORA_ACK_RETRIES + 1):
            success = self.lora.send_to_wait(
                message, self.parent_address, timeout=config.LORA_ACK_TIMEOUT_S
            )
            if success:
                logger.info(f"Επιτυχής αποστολή δεδομένων (προσπάθεια {attempt}): {payload}")
                return True
            logger.warning(f"Αποτυχία ACK στην προσπάθεια {attempt}/{config.LORA_ACK_RETRIES}")

        logger.error("Οριστική αποτυχία αποστολής μετά τις μέγιστες προσπάθειες.")
        return False

    def soft_sleep(self, duration_s: float):
        """'Ελαφρύ' sleep loop -- επιτρέπει μελλοντική επέκταση με έλεγχο
        battery-saving / interrupts χωρίς να μπλοκάρει εντελώς το process."""
        elapsed = 0.0
        while elapsed < duration_s:
            time.sleep(config.SLEEP_CHECK_INTERVAL_S)
            elapsed += config.SLEEP_CHECK_INTERVAL_S

    def run_forever(self):
        try:
            while True:
                payload = sensors.read_all()

                if payload["battery_voltage_v"] is not None and \
                        payload["battery_voltage_v"] < config.LOW_BATTERY_THRESHOLD_V:
                    logger.warning(
                        f"Χαμηλή μπαταρία ({payload['battery_voltage_v']}V). "
                        f"Ενεργοποίηση power-saving mode (διπλασιασμός διαστήματος)."
                    )
                    interval = config.READ_INTERVAL_S * 2
                else:
                    interval = config.READ_INTERVAL_S

                self.send_reading(payload)
                self.soft_sleep(interval)

        except KeyboardInterrupt:
            logger.info("Τερματισμός από χρήστη (Ctrl+C).")
        finally:
            sensors.cleanup()


if __name__ == "__main__":
    node = ChildNode()
    node.run_forever()
