"""
sensors.py - Ανάγνωση αισθητήρων Θυγατρικού Κόμβου
-----------------------------------------------------
Περιλαμβάνει:
  - DHT22 (θερμοκρασία / υγρασία αέρα)
  - Ανεμόμετρο (παλμικός αισθητήρας μέσω GPIO interrupt)
  - Αισθητήρας υγρασίας εδάφους (μέσω ADS1115 ADC)
  - Μέτρηση τάσης μπαταρίας (μέσω ADS1115 ADC + διαιρέτης τάσης)
"""

import time
import logging
import threading

import board
import busio
import adafruit_dht
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO

import config

logger = logging.getLogger("sensors")

# ---------- Αρχικοποίηση υλικού ----------
_dht_sensor = adafruit_dht.DHT22(getattr(board, f"D{config.DHT22_PIN}"))

_i2c = busio.I2C(board.SCL, board.SDA)
_ads = ADS1115(_i2c)
_soil_chan = AnalogIn(_ads, config.SOIL_ADC_CHANNEL)
_battery_chan = AnalogIn(_ads, config.BATTERY_ADC_CHANNEL)

GPIO.setmode(GPIO.BCM)
GPIO.setup(config.ANEMOMETER_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

_wind_pulse_count = 0
_wind_lock = threading.Lock()


def _wind_pulse_callback(channel):
    global _wind_pulse_count
    with _wind_lock:
        _wind_pulse_count += 1


GPIO.add_event_detect(config.ANEMOMETER_PIN, GPIO.FALLING,
                       callback=_wind_pulse_callback, bouncetime=5)


def read_dht22(max_retries=5):
    """Διαβάζει θερμοκρασία (°C) και υγρασία αέρα (%RH) από τον DHT22.
    Ο αισθητήρας μερικές φορές αποτυγχάνει στην ανάγνωση, γι' αυτό γίνονται retries."""
    for attempt in range(max_retries):
        try:
            temperature_c = _dht_sensor.temperature
            humidity = _dht_sensor.humidity
            if temperature_c is not None and humidity is not None:
                return round(temperature_c, 2), round(humidity, 2)
        except RuntimeError as e:
            logger.debug(f"DHT22 read retry {attempt+1}/{max_retries}: {e}")
            time.sleep(1.0)
    logger.warning("Αποτυχία ανάγνωσης DHT22 μετά από retries.")
    return None, None


def read_wind_speed(sample_window_s=None):
    """Μετρά την ταχύτητα ανέμου (m/s) μετρώντας παλμούς σε χρονικό παράθυρο."""
    global _wind_pulse_count
    window = sample_window_s or config.WIND_SAMPLE_WINDOW_S

    with _wind_lock:
        _wind_pulse_count = 0
    time.sleep(window)
    with _wind_lock:
        pulses = _wind_pulse_count

    pulses_per_sec = pulses / window
    wind_speed_ms = pulses_per_sec * config.ANEMOMETER_CALIBRATION
    return round(wind_speed_ms, 2)


def read_soil_moisture():
    """Επιστρέφει την υγρασία εδάφους ως ποσοστό (0-100%) βάσει βαθμονόμησης."""
    raw = _soil_chan.value
    dry, wet = config.SOIL_DRY_VALUE, config.SOIL_WET_VALUE
    pct = (dry - raw) / (dry - wet) * 100.0
    pct = max(0.0, min(100.0, pct))
    return round(pct, 1)


def read_battery_voltage():
    """Υπολογίζει την τάση μπαταρίας μέσω διαιρέτη τάσης στο ADS1115."""
    voltage = _battery_chan.voltage * config.BATTERY_DIVIDER_RATIO
    return round(voltage, 2)


def read_all():
    """Συγκεντρώνει όλες τις μετρήσεις σε ένα dict, έτοιμο για αποστολή μέσω LoRa."""
    temperature, humidity = read_dht22()
    wind_speed = read_wind_speed()
    soil_moisture = read_soil_moisture()
    battery_voltage = read_battery_voltage()

    return {
        "node_id": config.NODE_ID,
        "timestamp": time.time(),
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "wind_speed_ms": wind_speed,
        "soil_moisture_pct": soil_moisture,
        "battery_voltage_v": battery_voltage,
    }


def cleanup():
    """Καθαρισμός GPIO κατά το τερματισμό του προγράμματος."""
    GPIO.remove_event_detect(config.ANEMOMETER_PIN)
    GPIO.cleanup()
    _dht_sensor.exit()
