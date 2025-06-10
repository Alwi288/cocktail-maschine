import RPi.GPIO as GPIO
import time
import yaml
import os
import logging
# NEU: Datenbank-Manager importieren, um Kalibrierung zu lesen
import database_manager as db

# --- Logging Setup ---
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PumpController')
logger.setLevel(logging.DEBUG) # DEBUG für Tests
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)
# --------------------------------------------------------------------------

# Globale Variable für die Pin-Liste
PUMP_PINS = []
PUMP_COUNT = 8 # Feste Anzahl Pumpen

def load_config():
    """Lädt die Konfiguration und extrahiert die Pumpen-Pins."""
    global PUMP_PINS, PUMP_COUNT
    # Nur einmal laden
    if not PUMP_PINS:
        script_dir = os.path.dirname(__file__)
        config_path = os.path.join(script_dir, '..', 'config', 'config.yaml')
        logger.info(f"Lade Konfiguration von: {config_path}")
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                if 'pump_pins' in config and isinstance(config['pump_pins'], list):
                    PUMP_PINS = config['pump_pins']
                    PUMP_COUNT = len(PUMP_PINS) # Anzahl aus Config übernehmen
                    logger.info(f"{PUMP_COUNT} Pumpen-Pins geladen: {PUMP_PINS}")
                    return True
                else:
                    logger.error("Konfigurationsdatei fehlt 'pump_pins' oder es ist keine Liste.")
                    return False
        except FileNotFoundError:
            logger.error(f"Konfigurationsdatei nicht gefunden: {config_path}")
            return False
        except Exception as e:
            logger.error(f"Fehler beim Laden der Konfiguration: {e}")
            return False
    return True # Wenn PINS schon geladen waren

def setup_pumps():
    """Initialisiert die GPIO-Pins für die Pumpen."""
    if not load_config(): # Sicherstellen, dass Config geladen ist
         logger.error("Pumpen-Pins nicht geladen. Setup abgebrochen.")
         return False

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in PUMP_PINS:
            logger.debug(f"Setze Pin {pin} als OUTPUT, initial LOW")
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        logger.info("GPIO-Pins für Pumpen erfolgreich initialisiert.")
        return True
    except Exception as e:
        # Spezifischer Fehler für RPi.GPIO-Zugriffsprobleme
        if isinstance(e, RuntimeError) and "No access" in str(e):
             logger.critical("GPIO Zugriff fehlgeschlagen! Läuft das Skript mit nötigen Rechten (evtl. sudo) oder ist die Hardware korrekt initialisiert?")
        else:
             logger.error(f"Fehler beim Initialisieren der GPIO-Pins: {e}")
        return False

def turn_pump_on(pump_index):
    """Schaltet eine bestimmte Pumpe ein."""
    if 0 <= pump_index < len(PUMP_PINS):
        pin = PUMP_PINS[pump_index]
        logger.info(f"Schalte Pumpe {pump_index} (Pin {pin}) EIN")
        try:
            GPIO.output(pin, GPIO.HIGH)
        except Exception as e:
             logger.error(f"Fehler beim Einschalten von Pumpe {pump_index} (Pin {pin}): {e}")
    else:
        logger.warning(f"Ungültiger Pumpenindex: {pump_index}")

def turn_pump_off(pump_index):
    """Schaltet eine bestimmte Pumpe aus."""
    if 0 <= pump_index < len(PUMP_PINS):
        pin = PUMP_PINS[pump_index]
        logger.info(f"Schalte Pumpe {pump_index} (Pin {pin}) AUS")
        try:
            GPIO.output(pin, GPIO.LOW)
        except Exception as e:
             logger.error(f"Fehler beim Ausschalten von Pumpe {pump_index} (Pin {pin}): {e}")
    else:
        logger.warning(f"Ungültiger Pumpenindex: {pump_index}")

def dispense_duration(pump_index, duration_sec):
    """Lässt eine Pumpe für eine bestimmte Dauer laufen."""
    if duration_sec <= 0:
        logger.warning(f"Ungültige Dauer für Pumpe {pump_index}: {duration_sec}s")
        return
    if 0 <= pump_index < len(PUMP_PINS):
        pin = PUMP_PINS[pump_index]
        logger.info(f"Starte Pumpe {pump_index} (Pin {pin}) für {duration_sec:.2f} Sekunden.")
        try:
            GPIO.output(pin, GPIO.HIGH)
            start_time = time.monotonic()
            # Warte präziser als time.sleep für kurze Dauern
            while time.monotonic() - start_time < duration_sec:
                time.sleep(0.01) # Kurze Pause, um CPU nicht voll auszulasten
        except Exception as e:
             logger.error(f"Fehler während dispense_duration für Pumpe {pump_index}: {e}")
        finally:
            # Sicherstellen, dass die Pumpe ausgeschaltet wird
            GPIO.output(pin, GPIO.LOW)
            actual_duration = time.monotonic() - start_time
            logger.info(f"Stoppe Pumpe {pump_index} (Pin {pin}) nach {actual_duration:.2f}s (Ziel: {duration_sec:.2f}s).")
    else:
        logger.warning(f"Ungültiger Pumpenindex für dispense_duration: {pump_index}")


def dispense_ml(pump_index, volume_ml): # NEUE Funktion
    """Gibt eine bestimmte Menge (ml) über eine Pumpe aus, basierend auf Kalibrierung."""
    if not (0 <= pump_index < PUMP_COUNT):
         logger.error(f"Ungültiger Pumpenindex für dispense_ml: {pump_index}")
         return False
    if volume_ml <= 0:
        logger.warning(f"Ungültiges Volumen für dispense_ml: {volume_ml}ml")
        return False # Gebe 0ml nicht aus

    # Hole Kalibrierungswert aus der Datenbank
    pump_info = db.get_pump_info(pump_index)
    if pump_info is None:
         logger.error(f"Konnte Pumpeninfo für Index {pump_index} nicht laden.")
         return False

    calibration_ml_per_sec = pump_info[4] # Index 4 ist calibration_ml_per_sec

    if calibration_ml_per_sec is None or calibration_ml_per_sec <= 0:
        logger.error(f"Keine gültige Kalibrierung für Pumpe {pump_index} gefunden ({calibration_ml_per_sec}). Kann Menge nicht abgeben.")
        # Hier könnte man optional eine Standard-Rate annehmen oder abbrechen
        return False

    # Berechne benötigte Dauer
    try:
        duration_sec = float(volume_ml) / calibration_ml_per_sec
        logger.info(f"Berechnete Dauer für {volume_ml:.1f}ml an Pumpe {pump_index} (Rate: {calibration_ml_per_sec:.2f}ml/s): {duration_sec:.2f}s")
    except ZeroDivisionError:
         logger.error(f"Kalibrierung für Pumpe {pump_index} ist Null. Division durch Null.")
         return False
    except Exception as e:
         logger.error(f"Fehler bei Zeitberechnung für Pumpe {pump_index}: {e}")
         return False

    # Führe dispense_duration aus
    dispense_duration(pump_index, duration_sec)
    return True


def cleanup_gpio():
    """Gibt die GPIO-Ressourcen frei."""
    logger.info("Räume GPIO-Pins auf.")
    try:
         GPIO.cleanup()
    except Exception as e:
         # Fehler abfangen, falls GPIO nie initialisiert wurde
         logger.warning(f"Fehler beim GPIO Cleanup (evtl. nie initialisiert?): {e}")


# --- Code zum direkten Testen dieses Moduls ---
if __name__ == "__main__":
    print("--- Teste Pump Controller Modul (mit dispense_ml) ---")
    logger.setLevel(logging.DEBUG)

    # Stelle sicher, dass DB initialisiert ist (legt auch Pumpen 0-7 an)
    db.initialize_database()

    # Setze Test-Kalibrierungswert für Pumpe 0 (z.B. 5.0 ml/s)
    test_pump_index = 0
    test_calibration = 5.0 # ml/sec
    print(f"Setze Test-Kalibrierung für Pumpe {test_pump_index} auf {test_calibration} ml/s...")
    if not db.update_pump_calibration(test_pump_index, test_calibration):
        print("FEHLER: Konnte Test-Kalibrierung nicht in DB speichern.")
        # Hier abbrechen oder weitermachen? Vorerst weiter, dispense_ml wird fehlschlagen.

    # Lade Konfiguration und initialisiere GPIOs
    if load_config():
        if setup_pumps():
            print(f"Anzahl konfigurierter Pumpen: {PUMP_COUNT}")

            # Teste dispense_ml
            test_volume = 20 # ml
            print(f"\n-> Teste dispense_ml: {test_volume}ml an Pumpe {test_pump_index}...")

            # WICHTIG: Teste nur, wenn du sicher bist, was passiert!
            # Stelle sicher, dass Pumpe sicher laufen kann.
            if 0 <= test_pump_index < len(PUMP_PINS):
                try:
                    success = dispense_ml(test_pump_index, test_volume)
                    if success:
                         print(f"-> dispense_ml für Pumpe {test_pump_index} erfolgreich (laut Funktion).")
                    else:
                         print(f"-> dispense_ml für Pumpe {test_pump_index} ist fehlgeschlagen.")

                except Exception as e:
                    print(f"Fehler während des dispense_ml Tests: {e}")
                finally:
                    # GPIO-Pins am Ende des Tests aufräumen
                    cleanup_gpio()
            else:
                print(f"FEHLER: Test-Pumpenindex {test_pump_index} ist ungültig!")
                cleanup_gpio() # Trotzdem aufräumen
        else:
            print("FEHLER: GPIO-Setup fehlgeschlagen.")
            # Kein cleanup nötig, da setup fehlschlug
    else:
        print("FEHLER: Konfiguration konnte nicht geladen werden.")

    print("--- Test beendet ---")


