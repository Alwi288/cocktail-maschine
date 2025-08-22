# -*- coding: utf-8 -*-
# Kivy Imports
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty, DictProperty
from kivy.metrics import dp
from ui.cocktail_image_button import CocktailImageButton

# Standard Python Imports
import yaml
import os
import sys
import atexit
import traceback
import time

# Project Module Imports
try:
    # Ebene 0
    import database_manager as db
    import pump_controller as pc
    import core_logic as core
    print("INFO: Eigene Module (db, pc, core) erfolgreich importiert.")
# Error handling for module imports
except ImportError as e:
    # Ebene 0
    print(f"FEHLER: Konnte eigene Module nicht importieren: {e}")
    print("Stelle sicher, dass alle .py Dateien im 'src' Ordner sind und keine Syntaxfehler enthalten.")
    sys.exit(1) # Exit if essential modules are missing

# --- No central logging setup here for now ---
# Using basic print for feedback during debugging
print("INFO: Cocktail App startet...")


# --- Screen Class Definitions ---

class MainScreen(Screen): # Ebene 0
    """
    Hauptbildschirm: Zeigt verfügbare Cocktails an.
    """
    # Methode: Ebene 1 (4 spaces)
    def on_enter(self, *args):
        """Called when the screen becomes visible."""
        # Code: Ebene 2 (8 spaces)
        print("INFO: MainScreen betreten. Plane Populate...")
        # Schedule the population slightly delayed to ensure KV rules are applied
        Clock.schedule_once(self.populate_cocktails, 0)
        return super().on_enter(*args)

    # Methode: Ebene 1 (4 spaces)
    def populate_cocktails(self, dt):
        """Fetches available cocktails and creates buttons for them."""
        # Code: Ebene 2 (8 spaces)
        print(f"INFO: populate_cocktails (nach {dt:.4f}s Verzögerung) wird ausgeführt.")
        cocktail_list_widget = self.ids.get('cocktail_list_grid')
        if not cocktail_list_widget:
            print("FEHLER: GridLayout 'cocktail_list_grid' nicht im KV gefunden!")
            return

        cocktail_list_widget.clear_widgets() # Remove old buttons
        available_recipes = core.get_available_recipes() # Get available recipes from core logic

        if not available_recipes:
            print("INFO: Keine verfügbaren Cocktails gefunden.")
            # Optionally add a label indicating no cocktails are available
            cocktail_list_widget.height = dp(50) # Set minimum height
            return

        print(f"INFO: Füge {len(available_recipes)} Cocktails zur Liste hinzu...")
        button_height = dp(60) # Height for each button

        # Schleife: Ebene 2 (8 spaces)
        for recipe in available_recipes:
            # Code in Schleife: Ebene 3 (12 spaces)
            recipe_id, recipe_name, _, image_path, _ = recipe # Unpack recipe data
            # Create an image button for each cocktail
            btn = CocktailImageButton(
                recipe_id=recipe_id,
                source=image_path if image_path else '',
                size_hint_y=None,
                height=button_height,
            )
            btn.text = recipe_name  # Store recipe name for logging
            btn.bind(on_press=self.cocktail_selected) # Bind the on_press event
            cocktail_list_widget.add_widget(btn)

        # Code nach Schleife: Ebene 2 (8 spaces)
        # Update GridLayout height based on content
        spacing_y = cocktail_list_widget.spacing[1] if isinstance(cocktail_list_widget.spacing, (list, tuple)) else cocktail_list_widget.spacing
        cocktail_list_widget.height = len(available_recipes) * (button_height + spacing_y) - spacing_y if len(available_recipes) > 0 else 0

    # Methode: Ebene 1 (4 spaces)
    def cocktail_selected(self, instance):
        """Called when a cocktail button is pressed."""
        # Code: Ebene 2 (8 spaces)
        recipe_id = instance.recipe_id
        recipe_name = instance.text
        print(f"INFO: Cocktail '{recipe_name}' (ID: {recipe_id}) ausgewählt!")

        # 1. Get current glass size setting from DB
        selected_size_name = db.get_setting('SelectedGlassSize', default='Medium')
        print(f"INFO: Aktuell gewählte Glasgröße: '{selected_size_name}'")

        # 2. Determine target volume from config file
        target_volume_ml = 200.0 # Default fallback volume
        # try Block: Ebene 2 (8 spaces) - Corrected indentation
        try:
            # Code im try: Ebene 3 (12 spaces)
            # Construct path relative to this script (main.py in src/)
            script_dir = os.path.dirname(__file__)
            config_path = os.path.join(script_dir, '..', 'config', 'config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            if 'glass_sizes' in config and isinstance(config['glass_sizes'], dict):
                glass_sizes = config['glass_sizes']
                # Convert volume to float, use default if size name not found or invalid
                target_volume_ml = float(glass_sizes.get(selected_size_name, 200.0))
            print(f"INFO: Zielvolumen für '{selected_size_name}': {target_volume_ml}ml")
        except Exception as e: # except Block: Ebene 2 (8 spaces)
             # Code im except: Ebene 3 (12 spaces)
             print(f"FEHLER Config laden: {e}")
             # target_volume_ml keeps the default value from above

        # Code: Ebene 2 (8 spaces)
        # 3. Scale recipe ingredients
        scaled_ingredients = []
        if target_volume_ml > 0:
            # Code im if: Ebene 3 (12 spaces)
            print(f"INFO: Berechne skalierte Mengen für {target_volume_ml}ml...")
            scaled_ingredients = core.scale_recipe(recipe_id, target_volume_ml)
            if scaled_ingredients:
                # Code im if: Ebene 4 (16 spaces)
                print(f"--- Benötigte Zutaten für {recipe_name} ({selected_size_name} / {target_volume_ml}ml) ---")
                # List comprehension for printing scaled ingredients
                [print(f"  - {ing_name}: {amount:.1f} {unit} (ID: {ing_id})") for ing_id, ing_name, amount, unit in scaled_ingredients]
                print("---------------------------------------------------------------")
            else: # else: Ebene 3 (12 spaces)
                 # Code im else: Ebene 4 (16 spaces)
                 print(f"FEHLER: Skalierung fehlgeschlagen.")
        else: # else: Ebene 2 (8 spaces)
             # Code im else: Ebene 3 (12 spaces)
             print(f"FEHLER: Kein gültiges Zielvolumen.");

        # Code: Ebene 2 (8 spaces)
        # 4. Check ingredient availability (volume)
        if scaled_ingredients:
            # Code im if: Ebene 3 (12 spaces)
            print("INFO: Prüfe Verfügbarkeit der Zutaten...")
            is_available, details = core.check_ingredient_availability(scaled_ingredients)

            if is_available:
                # Code im if: Ebene 4 (16 spaces)
                print(f"INFO: {details['message']}")
                print("INFO: Starte Mixvorgang...")
                mix_success = True # Flag to track success
                pump_map = details['pump_map'] # Get mapping {ing_id: pump_index}
                dispensed_amounts = {} # Track dispensed amounts {pump_index: dispensed_ml}

                # --- Actual Dispensing Loop ---
                # TODO: Run this loop in a separate thread to avoid blocking UI!
                # Schleife: Ebene 4 (16 spaces)
                for ing_id, ing_name, scaled_amount, unit in scaled_ingredients:
                    # Code in Schleife: Ebene 5 (20 spaces)
                    pump_idx_to_use = pump_map.get(ing_id)
                    if pump_idx_to_use is not None:
                        # Code im if: Ebene 6 (24 spaces)
                        print(f"    -> Gebe {scaled_amount:.1f}ml von '{ing_name}' über Pumpe {pump_idx_to_use} aus...")
                        # Call pump controller to dispense the calculated amount
                        dispense_success = pc.dispense_ml(pump_idx_to_use, scaled_amount)
                        if not dispense_success:
                            print(f"FEHLER: Abgabe von '{ing_name}' fehlgeschlagen!")
                            mix_success = False
                            break # Abort mixing on error
                        else:
                            # Record amount dispensed for this pump
                            dispensed_amounts[pump_idx_to_use] = dispensed_amounts.get(pump_idx_to_use, 0) + scaled_amount
                    else: # else: Ebene 5 (20 spaces)
                         # This case should ideally not happen if check_availability passed
                         # Code im else: Ebene 6 (24 spaces)
                         print(f"FEHLER: Keine Pumpe für Zutat {ing_name} gefunden obwohl verfügbar?");
                         mix_success = False
                         break
                # Code nach Schleife: Ebene 4 (16 spaces)
                # --- After Mixing ---
                if mix_success:
                    # Code im if: Ebene 5 (20 spaces)
                    print("INFO: Mixvorgang erfolgreich. Aktualisiere DB...")
                    volume_update_success = True
                    # Schleife: Ebene 5 (20 spaces)
                    # Update database volume for each used pump
                    for pump_idx, dispensed_ml in dispensed_amounts.items():
                        # Code in Schleife: Ebene 6 (24 spaces)
                        pump_info_before = db.get_pump_info(pump_idx)
                        if pump_info_before:
                            # Code im if: Ebene 7 (28 spaces)
                            old_volume = pump_info_before[3] if pump_info_before[3] is not None else 0.0
                            new_volume = old_volume - dispensed_ml
                            print(f"    -> Pumpe {pump_idx}: Alt={old_volume:.1f}ml, Abgegeben={dispensed_ml:.1f}ml, Neu={new_volume:.1f}ml")
                            if not db.update_pump_volume(pump_idx, new_volume):
                                print(f"FEHLER: Volumen Update Pumpe {pump_idx}!");
                                volume_update_success = False # Mark failure but continue trying others
                        else: # else: Ebene 6 (24 spaces)
                             # Code im else: Ebene 7 (28 spaces)
                             print(f"FEHLER: Konnte alte Volumeninfo Pumpe {pump_idx} nicht laden.");
                             volume_update_success = False
                    # Code nach Schleife: Ebene 5 (20 spaces)
                    if not volume_update_success:
                        print("WARNUNG: Fehler beim Aktualisieren einiger Restmengen.")

                    # Add entry to pour log
                    log_id = db.add_pour_log_entry(recipe_id, target_volume_ml)
                    if log_id:
                        print(f"INFO: Cocktail im Logbuch (ID: {log_id}).")
                    else:
                        print("FEHLER: Konnte nicht ins Logbuch schreiben.")
                else: # else: Ebene 4 (16 spaces)
                    # Code im else: Ebene 5 (20 spaces)
                    print("FEHLER: Mixvorgang abgebrochen.")
            else: # else: Ebene 3 (12 spaces)
                 # Code im else: Ebene 4 (16 spaces)
                 print(f"FEHLER: {details['message']} -> Mixen nicht möglich.")
        else: # else: Ebene 2 (8 spaces)
             # Code im else: Ebene 3 (12 spaces)
             print("INFO: Mixen übersprungen.");


class ServiceMenuScreen(Screen): # Ebene 0
    # Methoden: Ebene 1 (4 spaces)
    def on_enter(self, *args):
        # Code: Ebene 2 (8 spaces)
        print("INFO: ServiceMenuScreen betreten.")
        pin_screen = self.manager.get_screen('pin_entry')
        if pin_screen: pin_screen.reset()
        return super().on_enter(*args)


class PumpAssignmentScreen(Screen): # Ebene 0
    # Properties: Ebene 1 (4 spaces)
    all_ingredient_data = [] # Cache for ingredient list

    # Methoden: Ebene 1 (4 spaces)
    def on_enter(self, *args):
        # Code: Ebene 2 (8 spaces)
        print("INFO: PumpAssignmentScreen betreten. Lade Pumpenzuordnung...")
        self.all_ingredient_data = db.get_all_ingredients()
        self.populate_pump_assignment()
        return super().on_enter(*args)

    def populate_pump_assignment(self):
        # Code: Ebene 2 (8 spaces)
        grid = self.ids.get('pump_assignment_grid')
        if not grid: print("FEHLER: GridLayout 'pump_assignment_grid' nicht gefunden!"); return
        grid.clear_widgets()
        current_pumps = db.get_all_pumps_info()
        current_assignment = {p[0]: (p[1], p[2]) for p in current_pumps}
        ingredient_names = ["---- Leer ----"] + [ing[1] for ing in self.all_ingredient_data]
        grid_height = 0; row_height = dp(40)
        # Schleife: Ebene 2 (8 spaces)
        for i in range(pc.PUMP_COUNT):
            # Code in Schleife: Ebene 3 (12 spaces)
            grid.add_widget(Label(text=f"Pumpe {i+1}:", size_hint_x=0.3, font_size='18sp'))
            _ , assigned_ing_name = current_assignment.get(i, (None, None))
            current_selection = assigned_ing_name if assigned_ing_name else "---- Leer ----"
            spinner = Spinner(text=current_selection, values=ingredient_names, size_hint_x=0.7, font_size='18sp', size_hint_y=None, height=row_height)
            spinner.pump_index = i
            spinner.bind(text=self.on_pump_assignment_change)
            grid.add_widget(spinner)
            grid_height += (row_height + grid.spacing[1])
        # Code nach Schleife: Ebene 2 (8 spaces)
        grid.height = grid_height - grid.spacing[1] if grid_height > 0 else 0

    def on_pump_assignment_change(self, spinner, selected_ingredient_name):
        # Code: Ebene 2 (8 spaces)
        pump_index = spinner.pump_index
        print(f"INFO: Pump {pump_index} assignment changed to '{selected_ingredient_name}'")
        selected_ingredient_id = None
        # if Block: Ebene 2 (8 spaces)
        if selected_ingredient_name != "---- Leer ----":
            # Schleife: Ebene 3 (12 spaces)
            for ing_id, ing_name in self.all_ingredient_data:
                # if Block: Ebene 4 (16 spaces)
                if ing_name == selected_ingredient_name: selected_ingredient_id = ing_id; break
        # if Block: Ebene 2 (8 spaces)
        if db.assign_ingredient_to_pump(pump_index, selected_ingredient_id):
            print(f"INFO: Zuweisung Pumpe {pump_index} gespeichert.")
        else:
            print(f"FEHLER: Zuweisung Pumpe {pump_index} nicht gespeichert!")


class CalibrationScreen(Screen): # Ebene 0
    # Properties: Ebene 1 (4 spaces)
    selected_pump_index = NumericProperty(-1)
    is_running = BooleanProperty(False)
    status_text = StringProperty("Pumpe 1-8 auswählen...")
    current_calibration_text = StringProperty("Aktuell: - ml/s")

    # Methoden: Ebene 1 (4 spaces)
    def on_enter(self, *args):
        # Code: Ebene 2 (8 spaces)
        self.reset_status()
        self.populate_pump_spinner()
        return super().on_enter(*args)

    def reset_status(self):
        # Code: Ebene 2 (8 spaces)
        self.selected_pump_index = -1; self.is_running = False
        if self.ids:
            # Code im if: Ebene 3 (12 spaces)
            self.ids.calibration_pump_spinner.text = "Wählen"
            self.ids.measured_volume_input.text = ""
            self.ids.measured_volume_input.disabled = True
            self.ids.start_calibration_button.disabled = True
            self.ids.save_calibration_button.disabled = True
            self.status_text = "Pumpe 1-8 auswählen..."
            self.current_calibration_text = "Aktuell: - ml/s"

    def populate_pump_spinner(self):
        # Code: Ebene 2 (8 spaces)
        spinner = self.ids.get('calibration_pump_spinner')
        if spinner: # Ebene 2 (8 spaces)
            # Code im if: Ebene 3 (12 spaces)
            spinner.values = [f"{i+1}" for i in range(pc.PUMP_COUNT)] # Display 1-8

    def on_spinner_select(self, text):
        # Code: Ebene 2 (8 spaces)
        try: # Ebene 2
            # Code im try: Ebene 3 (12 spaces)
            self.selected_pump_index = int(text) - 1
            assert 0 <= self.selected_pump_index < pc.PUMP_COUNT
            self.status_text = f"Pumpe {self.selected_pump_index + 1} ausgewählt."
            self.ids.start_calibration_button.disabled = False
            self.ids.measured_volume_input.disabled = True; self.ids.measured_volume_input.text = ""; self.ids.save_calibration_button.disabled = True
            pump_info = db.get_pump_info(self.selected_pump_index)
            if pump_info and pump_info[4] is not None and pump_info[4] > 0:
                self.current_calibration_text = f"Aktuell: {pump_info[4]:.2f} ml/s"
            else:
                self.current_calibration_text = "Aktuell: - ml/s (nicht kalibriert)"
        except (ValueError, AssertionError): # Ebene 2
             # Code im except: Ebene 3 (12 spaces)
             self.selected_pump_index = -1; self.status_text = "Gültige Pumpe (1-8) wählen."; self.ids.start_calibration_button.disabled = True; self.ids.save_calibration_button.disabled = True; self.current_calibration_text = "Aktuell: - ml/s"

    def start_calibration(self):
        # Code: Ebene 2 (8 spaces)
        if self.selected_pump_index == -1 or self.is_running: return
        self.is_running = True; self.ids.start_calibration_button.disabled = True; self.ids.calibration_pump_spinner.disabled = True; self.ids.measured_volume_input.disabled = True; self.ids.save_calibration_button.disabled = True; self.status_text = f"Pumpe {self.selected_pump_index + 1} läuft für 10 Sekunden..."; Clock.schedule_once(self._run_pump, 0.1)

    def _run_pump(self, dt):
        # Code: Ebene 2 (8 spaces)
        duration = 10.0; print(f"INFO: Starte Kalibrierlauf Pumpe {self.selected_pump_index} für {duration}s"); pc.dispense_duration(self.selected_pump_index, duration); print(f"INFO: Kalibrierlauf Pumpe {self.selected_pump_index} beendet.")
        self.is_running = False; self.ids.start_calibration_button.disabled = False; self.ids.calibration_pump_spinner.disabled = False; self.ids.measured_volume_input.disabled = False; self.ids.save_calibration_button.disabled = False; self.status_text = f"Lauf beendet. Menge (ml) eingeben & speichern."

    def save_calibration(self):
        # Code: Ebene 2 (8 spaces)
        if self.selected_pump_index == -1: self.status_text = "Fehler: Keine Pumpe ausgewählt."; return;
        try: # Ebene 2
            # Code im try: Ebene 3 (12 spaces)
            measured_volume = float(self.ids.measured_volume_input.text); assert measured_volume > 0
            calibration_duration = 10.0; ml_per_sec = measured_volume / calibration_duration; print(f"INFO: Speichere Kalibrierung Pumpe {self.selected_pump_index}: {ml_per_sec:.3f} ml/s")
            if db.update_pump_calibration(self.selected_pump_index, ml_per_sec):
                self.status_text = f"Gespeichert: {ml_per_sec:.2f} ml/s (Pumpe {self.selected_pump_index + 1})"; self.current_calibration_text = f"Aktuell: {ml_per_sec:.2f} ml/s"
            else: self.status_text = "Fehler beim Speichern in der DB!"
        except (ValueError, AssertionError): # Ebene 2
             # Code im except: Ebene 3 (12 spaces)
             self.status_text = f"Ungültige Eingabe (>0)!"
        except Exception as e: # Ebene 2
             # Code im except: Ebene 3 (12 spaces)
             self.status_text = f"Fehler: {e}"; print(f"FEHLER save_calibration: {e}"); traceback.print_exc()


class CleaningScreen(Screen): # Ebene 0
    # Properties: Ebene 1 (4 spaces)
    is_running = BooleanProperty(False)
    status_text = StringProperty("Bereit...")

    # Methoden: Ebene 1 (4 spaces)
    def on_enter(self, *args):
        # Code: Ebene 2 (8 spaces)
        self.reset_status()
        return super().on_enter(*args)

    def reset_status(self):
        # Code: Ebene 2 (8 spaces)
        self.is_running = False
        self.status_text = "Bereit. Schläuche in Reinigungsflüssigkeit/Wasser?"
        if self.ids: # Ebene 2 (8 spaces)
            self.ids.start_cleaning_button.disabled = False # Ebene 3 (12 spaces)

    def start_cleaning_cycle(self):
        # Code: Ebene 2 (8 spaces)
        if self.is_running: return
        try: # Ebene 2
            # Code im try: Ebene 3 (12 spaces)
            duration_str = db.get_setting("CleaningDurationPerPump", default="15")
            duration_per_pump = float(duration_str)
            assert duration_per_pump > 0
        except (ValueError, AssertionError, TypeError) as e: # Ebene 2
             # Code im except: Ebene 3 (12 spaces)
             print(f"WARNUNG: Reinigungsdauer ungültig ({e}). Verwende 15s."); duration_per_pump = 15.0
        # Code: Ebene 2 (8 spaces)
        self.is_running = True
        self.ids.start_cleaning_button.disabled = True
        self.status_text = f"Reinigung läuft (ca. {pc.PUMP_COUNT * duration_per_pump:.0f}s)..."
        Clock.schedule_once(lambda dt: self._run_cleaning(duration_per_pump), 0.1)

    def _run_cleaning(self, duration_per_pump):
        # Code: Ebene 2 (8 spaces)
        print(f"INFO: Starte Reinigungszyklus ({duration_per_pump}s pro Pumpe)...")
        # Schleife: Ebene 2 (8 spaces)
        for i in range(pc.PUMP_COUNT):
            # Code in Schleife: Ebene 3 (12 spaces)
            self.status_text = f"Reinige Pumpe {i+1}/{pc.PUMP_COUNT}..."
            print(f"INFO: Reinige Pumpe {i}...")
            pc.dispense_duration(i, duration_per_pump)
            print(f"INFO: Pumpe {i} fertig.")
        # Code nach Schleife: Ebene 2 (8 spaces)
        self.is_running = False
        self.ids.start_cleaning_button.disabled = False
        self.status_text = "Reinigungszyklus abgeschlossen."
        print("INFO: Reinigungszyklus beendet.")


class PinEntryScreen(Screen): # Ebene 0
    # Properties: Ebene 1 (4 spaces)
    status_text = StringProperty("Bitte Techniker-PIN eingeben:")
    entered_pin = StringProperty("")

    # Methoden: Ebene 1 (4 spaces)
    def on_enter(self, *args):
        # Code: Ebene 2 (8 spaces)
        self.reset()
        return super().on_enter(*args)

    def reset(self):
        # Code: Ebene 2 (8 spaces)
        self.entered_pin = ""
        self.status_text = "Bitte Techniker-PIN eingeben:"
        if self.ids:
            # Code im if: Ebene 3 (12 spaces)
            self.ids.pin_input.text = ""

    def check_pin(self):
        # Code: Ebene 2 (8 spaces)
        correct_pin = db.get_setting("TechnicianPIN")
        if correct_pin is None:
            # Code im if: Ebene 3 (12 spaces)
            self.status_text = "FEHLER: Kein PIN in DB!"
            print("FEHLER: TechnicianPIN nicht in settings!")
            return
        # Code: Ebene 2 (8 spaces)
        if self.entered_pin == correct_pin:
            # Code im if: Ebene 3 (12 spaces)
            print("INFO: PIN korrekt. Wechsle zum Techniker-Menü.")
            self.status_text = "PIN OK!"
            self.manager.transition = SlideTransition(direction="left")
            self.manager.current = 'tech_menu'
        else:
            # Code im else: Ebene 3 (12 spaces)
            print("WARNUNG: Falscher PIN.")
            self.status_text = "Falscher PIN! Erneut versuchen."
            self.ids.pin_input.text = ""
            self.entered_pin = ""


class TechnicianMenuScreen(Screen): # Ebene 0
    pass # Ebene 1


# NEUE Klasse für den Einstellungs-Screen
class SettingsScreen(Screen): # Ebene 0
    # Properties zum Binden an die UI-Elemente in KV
    # Wir laden die Startwerte in on_enter
    current_pin = StringProperty("")
    current_glass_size = StringProperty("Medium") # Default
    current_cleaning_duration = StringProperty("15") # Default
    status_text = StringProperty("")
    glass_size_options = ListProperty([]) # Liste für Spinner

    # Methoden: Ebene 1 (4 spaces)
    def on_enter(self, *args):
        """Lädt aktuelle Einstellungen aus DB und Config beim Betreten."""
        # Code: Ebene 2 (8 spaces)
        print("INFO: SettingsScreen betreten. Lade Einstellungen...")
        self.load_settings()
        return super().on_enter(*args)

    def load_settings(self):
        """Lädt aktuelle Werte und füllt die UI."""
        # Code: Ebene 2 (8 spaces)
        # Lade aktuellen PIN (oder Standard aus Config als Fallback?)
        # Besser: Nur aus DB laden, Init muss sicherstellen, dass er da ist.
        pin = db.get_setting("TechnicianPIN")
        if pin is None:
            print("FEHLER: TechnicianPIN nicht in DB gefunden!")
            pin = "1234" # Fallback? Oder Fehlermeldung?
            self.status_text = "FEHLER: PIN nicht in DB!"
        self.current_pin = pin
        # Update TextInput explizit, da Property-Bindung in KV manchmal zögert
        if self.ids.setting_pin_input: self.ids.setting_pin_input.text = pin


        # Lade aktuelle Glasgröße
        size = db.get_setting("SelectedGlassSize", default="Medium")
        self.current_glass_size = size
        if self.ids.setting_glass_spinner: self.ids.setting_glass_spinner.text = size


        # Lade aktuelle Reinigungsdauer
        duration = db.get_setting("CleaningDurationPerPump", default="15")
        self.current_cleaning_duration = duration
        if self.ids.setting_cleaning_input: self.ids.setting_cleaning_input.text = duration


        # Lade Glasgrößen-Optionen aus Config für Spinner
        options = ["Medium"] # Default Fallback
        try: # Ebene 2
            # Code im try: Ebene 3 (12 spaces)
            script_dir = os.path.dirname(__file__)
            config_path = os.path.join(script_dir, '..', 'config', 'config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            if 'glass_sizes' in config and isinstance(config['glass_sizes'], dict):
                options = list(config['glass_sizes'].keys())
            else:
                print("WARNUNG: glass_sizes nicht in Config gefunden.")
        except Exception as e: # Ebene 2
             # Code im except: Ebene 3 (12 spaces)
             print(f"FEHLER Config laden für Glasgrößen: {e}")
        # Code: Ebene 2 (8 spaces)
        self.glass_size_options = options
        if self.ids.setting_glass_spinner: self.ids.setting_glass_spinner.values = options

        self.status_text = "Einstellungen geladen."


    def save_settings(self):
        """Speichert die geänderten Einstellungen in der DB."""
        # Code: Ebene 2 (8 spaces)
        print("INFO: Speichere Einstellungen...")
        all_saved = True

        # PIN speichern (Validierung?)
        new_pin = self.ids.setting_pin_input.text
        if new_pin and len(new_pin) >= 4: # Einfache Längenprüfung
            if db.set_setting("TechnicianPIN", new_pin):
                print("INFO: Neuer PIN gespeichert.")
            else:
                print("FEHLER: PIN konnte nicht gespeichert werden.")
                all_saved = False
        else:
            print("WARNUNG: Ungültiger PIN (min. 4 Zeichen) - nicht gespeichert.")
            self.status_text = "PIN ungültig (min 4 Zeichen)!"
            # Lade alten Wert neu, um UI zu korrigieren
            self.current_pin = db.get_setting("TechnicianPIN", "")
            if self.ids.setting_pin_input: self.ids.setting_pin_input.text = self.current_pin
            all_saved = False # Markiere als nicht erfolgreich

        # Glasgröße speichern
        new_size = self.ids.setting_glass_spinner.text
        if new_size in self.glass_size_options: # Prüfe ob Wert gültig ist
             if db.set_setting("SelectedGlassSize", new_size):
                 print("INFO: Neue Glasgröße gespeichert.")
             else:
                 print("FEHLER: Glasgröße konnte nicht gespeichert werden.")
                 all_saved = False
        else:
             print(f"WARNUNG: Ungültige Glasgröße '{new_size}' ausgewählt?")
             all_saved = False

        # Reinigungsdauer speichern (Validierung?)
        new_duration = self.ids.setting_cleaning_input.text
        try: # Ebene 2
            # Code im try: Ebene 3 (12 spaces)
            duration_val = int(new_duration)
            if duration_val > 0:
                if db.set_setting("CleaningDurationPerPump", str(duration_val)):
                     print("INFO: Neue Reinigungsdauer gespeichert.")
                else:
                     print("FEHLER: Reinigungsdauer konnte nicht gespeichert werden.")
                     all_saved = False
            else:
                 # Code im else: Ebene 4 (16 spaces)
                 print("WARNUNG: Reinigungsdauer muss > 0 sein - nicht gespeichert.")
                 self.status_text = "Dauer ungültig (>0)!"
                 # Lade alten Wert neu
                 self.current_cleaning_duration = db.get_setting("CleaningDurationPerPump", "15")
                 if self.ids.setting_cleaning_input: self.ids.setting_cleaning_input.text = self.current_cleaning_duration
                 all_saved = False
        except ValueError: # Ebene 2
             # Code im except: Ebene 3 (12 spaces)
             print(f"WARNUNG: Ungültige Eingabe für Reinigungsdauer '{new_duration}' - nicht gespeichert.")
             self.status_text = "Dauer ungültig (Zahl)!"
             # Lade alten Wert neu
             self.current_cleaning_duration = db.get_setting("CleaningDurationPerPump", "15")
             if self.ids.setting_cleaning_input: self.ids.setting_cleaning_input.text = self.current_cleaning_duration
             all_saved = False

        # Code: Ebene 2 (8 spaces)
        if all_saved:
            self.status_text = "Einstellungen erfolgreich gespeichert!"
            # Optional: Kurz anzeigen und zurück navigieren
            # Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'tech_menu'), 1.5)
        else:
            # Status wurde schon bei Fehler gesetzt
            pass


# Der Screen Manager
class WindowManager(ScreenManager): # Ebene 0
    pass # Ebene 1

# Die Haupt-App Klasse
class CocktailApp(App): # Ebene 0
    # Methoden: Ebene 1 (4 spaces)
    def build(self):
        # Code: Ebene 2 (8 spaces)
        print("INFO: build() - Initialisiere Datenbank...")
        db.initialize_database()
        print("INFO: build() - Initialisiere Pumpen-GPIOs...")
        if not pc.setup_pumps(): print("WARNUNG: GPIO Setup fehlgeschlagen.")
        atexit.register(self.on_stop)
        print("INFO: build() - Lade KV Datei explizit...")
        # try Block: Ebene 2 (8 spaces)
        try:
             # Code im try: Ebene 3 (12 spaces)
             kv_file = os.path.join(os.path.dirname(__file__), 'cocktail.kv')
             # Explicitly load the KV file and return the root widget
             widget = Builder.load_file(kv_file)
             print(f"INFO: build() - KV-Datei '{kv_file}' explizit geladen. Root ist: {widget}")
             return widget
        except Exception as e: # Ebene 2
             # Code im except: Ebene 3 (12 spaces)
             print(f"FEHLER: Konnte KV Datei nicht laden: {e}"); traceback.print_exc(); return None

    def on_start(self): # Ebene 1
        # Code: Ebene 2 (8 spaces)
        print("INFO: on_start() - App Fenster ist erstellt.")
        pass # Nothing needed here currently

    def on_stop(self): # Ebene 1
        # Code: Ebene 2 (8 spaces)
        print("INFO: Cocktail App wird beendet. Räume GPIOs auf.")
        pc.cleanup_gpio()

# --- App starten ---
if __name__ == '__main__': # Ebene 0
    print("INFO: Starte App Ausführung...")
    try: # Ebene 1 (4 spaces)
        CocktailApp().run()
        print("INFO: App normal beendet.") # Ebene 2 (8 spaces)
    except KeyboardInterrupt: # Ebene 1
         print("INFO: App durch Benutzer (Strg+C) beendet.") # Ebene 2
    except Exception as e: # Ebene 1
         # Ebene 2 (8 spaces)
         print(f">>> FEHLER: Unerwarteter Fehler in der App: {e}")
         import traceback
         traceback.print_exc()
         # Ebene 2 (8 spaces) - Nested try for cleanup
         try:
             # Ebene 3 (12 spaces)
             pc.cleanup_gpio()
         except Exception as cleanup_e: # Ebene 2
             # Ebene 3 (12 spaces)
             print(f"FEHLER beim GPIO Cleanup im Fehlerfall: {cleanup_e}")
