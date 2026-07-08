"""
config.py - Ρυθμίσεις Θυγατρικού Κόμβου (Child Node)
-----------------------------------------------------
Κεντρικό αρχείο παραμετροποίησης. Προσαρμόστε τα pins/τιμές
ανάλογα με το πραγματικό σας καλωδίωμα.
"""

# ---------- Ταυτότητα κόμβου ----------
NODE_ID = "C1"                # Μοναδικό αναγνωριστικό θυγατρικού κόμβου (C1..CN)
PARENT_NODE_ID = "P1"         # Ο γονικός κόμβος στον οποίο ανήκει

# ---------- LoRa (SPI - RFM95/SX1276) ----------
LORA_FREQUENCY = 868.0        # MHz (868 για Ευρώπη, 915 για Η.Π.Α.)
LORA_SPI_CHANNEL = 0          # SPI0 στο Raspberry Pi
LORA_INTERRUPT_PIN = 24       # GPIO pin συνδεδεμένο στο DIO0 του module
LORA_RESET_PIN = 25           # GPIO pin συνδεδεμένο στο RESET του module
LORA_TX_POWER = 14            # dBm - χαμηλή κατανάλωση ενέργειας
LORA_ACK_RETRIES = 3          # Προσπάθειες επανεκπομπής αν δεν έρθει ACK
LORA_ACK_TIMEOUT_S = 2.0

# ---------- Αισθητήρες ----------
DHT22_PIN = 4                 # GPIO pin του DHT22 (θερμοκρασία/υγρασία αέρα)

ANEMOMETER_PIN = 17           # GPIO pin παλμικού αισθητήρα ανέμου (reed switch)
ANEMOMETER_RADIUS_CM = 9.0    # Ακτίνα κυπέλλων ανεμόμετρου (βαθμονόμηση)
ANEMOMETER_CALIBRATION = 2.4  # Συντελεστής βαθμονόμησης (m/s ανά παλμό/δευτ.)
WIND_SAMPLE_WINDOW_S = 5.0    # Διάρκεια μέτρησης παλμών ανέμου

SOIL_ADC_CHANNEL = 0          # Κανάλι ADS1115 (0-3) για αισθητήρα υγρασίας εδάφους
SOIL_DRY_VALUE = 26000        # Τιμή ADC για ξηρό έδαφος (βαθμονόμηση)
SOIL_WET_VALUE = 9000         # Τιμή ADC για κορεσμένο-υγρό έδαφος (βαθμονόμηση)

# ---------- Διαχείριση Ενέργειας ----------
READ_INTERVAL_S = 300         # Χρονικό διάστημα μεταξύ μετρήσεων (π.χ. 300s = 5 λεπτά)
SLEEP_CHECK_INTERVAL_S = 1    # Βήμα ελέγχου κατά το "ελαφρύ" sleep (soft sleep loop)
LOW_BATTERY_THRESHOLD_V = 3.3 # Κατώφλι μπαταρίας για ενεργοποίηση power-saving mode
BATTERY_ADC_CHANNEL = 1       # Κανάλι ADS1115 για μέτρηση τάσης μπαταρίας (voltage divider)
BATTERY_DIVIDER_RATIO = 2.0   # Λόγος διαιρέτη τάσης (π.χ. 2x αν R1=R2)

# ---------- Logging ----------
LOG_FILE = "child_node.log"
LOG_LEVEL = "INFO"
