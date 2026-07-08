# IoT Ιεραρχική Δομή Ακμών - Θυγατρικοί & Γονικοί Κόμβοι

Υλοποίηση σε Python για Raspberry Pi της αρχιτεκτονικής:

```
[C1..CN] --LoRa (10-15χλμ, χαμηλή κατανάλωση)--> [P1..PM] --Wi-Fi--> [Supabase / Cloud]
```

## Δομή αρχείων

```
child_node/
  config.py       # Ρυθμίσεις pins, βαθμονομήσεις, χρονισμοί
  sensors.py       # DHT22, ανεμόμετρο, υγρασία εδάφους, μπαταρία
  main_child.py    # Κύριος βρόχος: μέτρηση -> αποστολή LoRa -> sleep

parent_node/
  config.py           # Ρυθμίσεις LoRa, όρια επικύρωσης, Supabase creds
  local_db.py         # Ελαφριά SQLite βάση buffering + dedup
  supabase_sync.py    # Background thread συγχρονισμού με Supabase
  main_parent.py      # LoRa gateway: λήψη -> validation -> buffer -> sync

requirements_child.txt
requirements_parent.txt
```

## 1. Εγκατάσταση - Θυγατρικός Κόμβος (Ci)

Υλικό: Raspberry Pi (π.χ. Zero W) + RFM95/SX1276 LoRa module (SPI) + DHT22 +
παλμικό ανεμόμετρο + αισθητήρας υγρασίας εδάφους μέσω ADS1115 (I2C).

```bash
sudo raspi-config   # Ενεργοποίηση SPI και I2C interfaces
pip3 install -r requirements_child.txt
```

Προσαρμόστε το `child_node/config.py`:
- `NODE_ID` (π.χ. "C1", "C2", ...)
- GPIO pins ανάλογα με το καλωδίωμά σας
- Τιμές βαθμονόμησης (`ANEMOMETER_CALIBRATION`, `SOIL_DRY_VALUE`, `SOIL_WET_VALUE`)

Εκτέλεση:
```bash
cd child_node
python3 main_child.py
```

## 2. Εγκατάσταση - Γονικός Κόμβος (Pi)

Υλικό: Raspberry Pi (πιο ικανό μοντέλο, π.χ. Pi 4) + RFM95/SX1276 LoRa module
+ ενεργή σύνδεση Wi-Fi.

```bash
pip3 install -r requirements_parent.txt
```

Προσαρμόστε το `parent_node/config.py`:
- `SUPABASE_URL`, `SUPABASE_KEY` (από το Supabase project settings)
- `SUPABASE_TABLE` (π.χ. "sensor_readings")
- Όρια επικύρωσης `VALID_RANGES` ανά είδος αισθητήρα

### Πίνακας Supabase (SQL)

```sql
create table sensor_readings (
  id bigserial primary key,
  node_id text not null,
  parent_id text not null,
  timestamp double precision not null,
  temperature_c double precision,
  humidity_pct double precision,
  wind_speed_ms double precision,
  soil_moisture_pct double precision,
  battery_voltage_v double precision,
  received_at double precision not null,
  unique (node_id, timestamp)
);
```

Εκτέλεση:
```bash
cd parent_node
python3 main_parent.py
```

## Σημειώσεις / Περιορισμοί

- Η βιβλιοθήκη `raspi-lora` υποθέτει καλωδίωση RFM95 μέσω SPI0 με DIO0 στο
  interrupt pin. Αν χρησιμοποιείτε διαφορετικό module (π.χ. μέσω UART σε
  ξεχωριστό microcontroller), θα χρειαστεί να αντικαταστήσετε το layer
  επικοινωνίας LoRa στα `main_child.py` / `main_parent.py`.
- Το Raspberry Pi δεν υποστηρίζει πραγματικό hardware deep-sleep όπως ένα
  ESP32. Το `soft_sleep()` στον θυγατρικό κόμβο είναι ένα λογισμικού-επίπεδο
  duty-cycling. Αν το πραγματικό ενεργειακό προφίλ του θυγατρικού κόμβου
  είναι κρίσιμο, εξετάστε ESP32 (MicroPython/C) αντί για Raspberry Pi εκεί,
  διατηρώντας Raspberry Pi μόνο στον Γονικό Κόμβο.
- Το dedup στη `local_db.py` γίνεται με UNIQUE(node_id, timestamp) και
  επιπλέον χρονικό παράθυρο, ώστε retransmissions λόγω αναξιόπιστου LoRa
  link να μη δημιουργούν διπλότυπες εγγραφές.
- Το `upsert(... on_conflict="node_id,timestamp")` στο Supabase απαιτεί το
  αντίστοιχο UNIQUE constraint να υπάρχει ήδη στον πίνακα (βλ. SQL παραπάνω).
