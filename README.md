# Cocktail Maschine

## Projektziel
Das Projekt automatisiert das Mischen von Cocktails. Eine Python-App steuert mehrere Pumpen, verwaltet Rezepte und bietet eine grafische Oberfläche zur Bedienung.

## Hardwarevoraussetzungen
- Raspberry Pi mit GPIO-Unterstützung
- 8 (oder mehr) Pumpen samt Treibern (Relais/Transistoren)
- Netzteil für Raspberry Pi und Pumpen

## Benötigte Python-Pakete
- [Kivy](https://kivy.org/) für die Benutzeroberfläche
- [PyYAML](https://pyyaml.org/) zum Laden der Konfiguration
- [RPi.GPIO](https://pypi.org/project/RPi.GPIO/) zur Ansteuerung der Pumpen (nur auf dem Raspberry Pi erforderlich)
- [pytest](https://pytest.org/) für Tests

## Setup
1. **Datenbank initialisieren**
   ```
   python -c "from src import database_manager as db; db.initialize_database()"
   ```
2. **Konfigurationsdatei anpassen**
   Passe `config/config.yaml` an deine Hardware (z. B. `pump_pins`) und Einstellungen an.
3. **App starten**
   ```
   python src/main.py
   ```

## Hinweise zur Ausführung auf dem Raspberry Pi
- Stelle sicher, dass alle benötigten Pakete installiert sind (`sudo apt install python3-kivy python3-rpi.gpio` oder über `pip`).
- Führe die App bei Bedarf mit erhöhten Rechten aus (`sudo`), damit die GPIO-Pins genutzt werden können.
- Ein angeschlossener Bildschirm oder eine geeignete Kivy-Konfiguration (z. B. Framebuffer) wird benötigt.

## Tests
- Starte die Tests mit:
  ```
  pytest
  ```
- Für Kivy-Tests kann eine laufende Display-Umgebung notwendig sein.
