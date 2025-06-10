import logging
import yaml
import os
import database_manager as db # Stelle sicher, dass db importiert ist

# --- Logging Setup ---
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CoreLogic')
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)
# ---------------------

# --- get_available_recipes ---
# (Unverändert von oben)
def get_available_recipes():
    available_recipes = []
    all_recipes = db.get_all_recipes()
    all_pumps_info = db.get_all_pumps_info()
    assigned_ingredient_ids = set()
    for pump_info in all_pumps_info:
        if pump_info[1] is not None:
            assigned_ingredient_ids.add(pump_info[1])
    logger.debug(f"Zugewiesene Zutaten-IDs: {assigned_ingredient_ids}")
    if not assigned_ingredient_ids:
        # logger.warning("Keine Zutaten den Pumpen zugewiesen...") # Weniger Warnungen
        return []
    for recipe in all_recipes:
        recipe_id = recipe[0]
        recipe_name = recipe[1]
        required_ingredients_info = db.get_ingredients_for_recipe(recipe_id)
        if not required_ingredients_info:
            # logger.warning(f"Rezept '{recipe_name}' hat keine Zutaten...")
            continue
        required_ingredient_ids = set()
        all_ingredients_found_in_db = True
        for req_ing_info in required_ingredients_info:
            ing_name = req_ing_info[0]
            ingredient = db.get_ingredient_by_name(ing_name)
            if ingredient:
                required_ingredient_ids.add(ingredient[0])
            else:
                logger.error(f"Zutat '{ing_name}' für Rezept '{recipe_name}' nicht in Zutatenliste gefunden!")
                all_ingredients_found_in_db = False
                break
        if not all_ingredients_found_in_db:
            continue
        logger.debug(f"Rezept '{recipe_name}': Benötigt IDs: {required_ingredient_ids}")
        if required_ingredient_ids.issubset(assigned_ingredient_ids):
            logger.debug(f"Rezept '{recipe_name}' ist verfügbar (basierend auf Zuweisung).")
            available_recipes.append(recipe)
        else:
            missing_ids = required_ingredient_ids.difference(assigned_ingredient_ids)
            logger.debug(f"Rezept '{recipe_name}' ist NICHT verfügbar. Fehlende Zutat-IDs: {missing_ids}")
    logger.info(f"Insgesamt {len(available_recipes)} Rezepte potenziell verfügbar.")
    return available_recipes


# --- scale_recipe ---
# (Unverändert von oben)
def scale_recipe(recipe_id, target_total_volume_ml):
    logger.debug(f"Skaliere Rezept ID {recipe_id} auf {target_total_volume_ml}ml Gesamtvolumen.")
    base_ingredients = db.get_ingredients_for_recipe(recipe_id)
    if not base_ingredients:
        logger.warning(f"Keine Basiszutaten für Rezept ID {recipe_id} gefunden...")
        return []
    standard_total_volume_ml = 0
    ingredients_to_scale = []
    for ing_name, amount, unit in base_ingredients:
        try: amount_f = float(amount)
        except (ValueError, TypeError): continue
        if unit.lower() == 'ml':
            standard_total_volume_ml += amount_f
            ingredient = db.get_ingredient_by_name(ing_name)
            if ingredient: ingredients_to_scale.append({'id': ingredient[0], 'name': ing_name, 'base_amount': amount_f, 'unit': unit})
            else: logger.error(f"Konnte ID für Zutat '{ing_name}' beim Skalieren nicht finden.")
        else: logger.warning(f"Zutat '{ing_name}' mit Einheit '{unit}' kann nicht skaliert werden...")
    if standard_total_volume_ml <= 0:
        logger.warning(f"Standardrezept ID {recipe_id} hat kein Volumen...")
        return []
    try: scaling_factor = float(target_total_volume_ml) / standard_total_volume_ml
    except ZeroDivisionError: return []
    except Exception as e: logger.error(f"Fehler bei Skalierungsfaktor: {e}"); return []
    logger.debug(f"Standardvolumen: {standard_total_volume_ml}ml, Ziellvolumen: {target_total_volume_ml}ml, Faktor: {scaling_factor:.4f}")
    scaled_ingredients = []
    for ing_data in ingredients_to_scale:
        scaled_amount = ing_data['base_amount'] * scaling_factor
        scaled_ingredients.append((ing_data['id'], ing_data['name'], scaled_amount, ing_data['unit']))
        logger.debug(f"  {ing_data['name']}: {ing_data['base_amount']:.1f}{ing_data['unit']} -> {scaled_amount:.1f}{ing_data['unit']}")
    return scaled_ingredients


# --- Verfügbarkeitsprüfung --- NEUE FUNKTION
def check_ingredient_availability(scaled_ingredients):
    """
    Prüft, ob für alle skalierten Zutaten genug Volumen an den zugewiesenen Pumpen vorhanden ist.

    Args:
        scaled_ingredients (list): Liste von Tupeln (ing_id, ing_name, scaled_amount, unit)

    Returns:
        tuple: (bool, dict) -> (True/False, details)
               details ist ein Dict:
               Bei True: {'pump_map': {ingredient_id: pump_index}, 'message': 'Alle Zutaten verfügbar.'}
               Bei False: {'missing': [(name, required, available, unit)], 'message': 'Nicht genug von Zutat X...'}
    """
    logger.debug("Prüfe Zutatenverfügbarkeit (Volumen)...")
    all_pumps = db.get_all_pumps_info() # Holt [(idx, ing_id, ing_name, vol, calib), ...]

    # Erstelle Mappings für leichtere Suche: Zutat -> Pumpe, Pumpe -> Volumen
    ingredient_to_pump = {}
    pump_volumes = {}
    for p_idx, ing_id, _, vol, _ in all_pumps:
        if ing_id is not None:
            ingredient_to_pump[ing_id] = p_idx
        pump_volumes[p_idx] = vol if vol is not None else 0.0

    logger.debug(f"Pumpen-Mapping: {ingredient_to_pump}")
    logger.debug(f"Pumpen-Volumen: {pump_volumes}")

    missing_or_low = []
    pump_map_for_recipe = {} # Speichert, welche Pumpe für welche Zutat gebraucht wird

    for ing_id, ing_name, scaled_amount, unit in scaled_ingredients:
        if unit.lower() != 'ml': # Prüfe nur ml-Angaben
            continue

        pump_index = ingredient_to_pump.get(ing_id)

        if pump_index is None:
            # Sollte durch get_available_recipes schon ausgeschlossen sein, aber zur Sicherheit
            logger.warning(f"Keine Pumpe für benötigte Zutat '{ing_name}' (ID: {ing_id}) gefunden!")
            missing_or_low.append((ing_name, scaled_amount, 0.0, unit, "Keine Pumpe zugewiesen"))
            continue # Nächste Zutat prüfen

        # Pumpe gefunden, jetzt Volumen prüfen
        current_volume = pump_volumes.get(pump_index, 0.0)
        if current_volume < scaled_amount:
            logger.warning(f"Nicht genug von '{ing_name}' (ID: {ing_id}) an Pumpe {pump_index}. Benötigt: {scaled_amount:.1f}ml, Vorhanden: {current_volume:.1f}ml")
            missing_or_low.append((ing_name, scaled_amount, current_volume, unit, f"Pumpe {pump_index}"))
        else:
            # Diese Zutat ist ok, merke dir die Pumpe
            pump_map_for_recipe[ing_id] = pump_index
            logger.debug(f"'{ing_name}' (ID: {ing_id}) an Pumpe {pump_index} OK. Benötigt: {scaled_amount:.1f}ml, Vorhanden: {current_volume:.1f}ml")

    if not missing_or_low:
        logger.info("Alle benötigten Zutaten in ausreichender Menge verfügbar.")
        return True, {'pump_map': pump_map_for_recipe, 'message': 'Alle Zutaten verfügbar.'}
    else:
        # Erstelle detaillierte Fehlermeldung
        error_msg = "Nicht genug Zutaten verfügbar: "
        details = []
        for name, req, avail, unit, loc in missing_or_low:
            details.append(f"{name} ({req:.1f}{unit} benötigt, nur {avail:.1f}{unit} auf {loc})")
        error_msg += "; ".join(details)
        logger.warning(error_msg)
        return False, {'missing': missing_or_low, 'message': error_msg}


# --- Testblock ---
# (if __name__ == '__main__': ... bleibt unverändert)
if __name__ == '__main__':
    print("--- Teste Core Logic ---")
    logger.setLevel(logging.DEBUG)
    db.initialize_database()
    try:
        # Stelle sicher, dass Testdaten vorhanden sind
        # (Diese Aufrufe initialisieren/weisen Pumpen etc. zu)
        db.test_ingredients()
        db.test_recipes()
        db.test_recipe_ingredients()
        db.test_pumps() # Setzt Volumen für Pumpe 0, 1, 2
        # db.test_settings()
        # db.test_pour_log()
    except AttributeError as e:
        print(f"WARNUNG: Testfunktionen nicht ausführbar: {e}")

    print("\nErmittle verfügbare Rezepte...")
    recipes_ready = get_available_recipes()
    # ... (Rest des Verfügbarkeitstests)

    print("\n--- Teste Rezept Skalierung ---")
    cuba_libre_recipe = db.get_recipe_by_name("Cuba Libre")
    if cuba_libre_recipe:
        recipe_id_to_scale = cuba_libre_recipe[0]
        # ... (Rest des Skalierungstests) ...
        scaled_result = scale_recipe(recipe_id_to_scale, 200.0) # Test für Medium

        # --- NEU: Verfügbarkeit für skaliertes Rezept testen ---
        if scaled_result:
             print("\nPrüfe Verfügbarkeit für skalierten Cuba Libre (Medium):")
             is_available, details = check_ingredient_availability(scaled_result)
             print(f"Verfügbar: {is_available}")
             print(f"Details: {details}")

             # Teste mit unrealistisch hoher Menge
             print("\nPrüfe Verfügbarkeit für skalierten Cuba Libre (5000ml):")
             scaled_large = scale_recipe(recipe_id_to_scale, 5000.0)
             is_available_large, details_large = check_ingredient_availability(scaled_large)
             print(f"Verfügbar: {is_available_large}")
             print(f"Details: {details_large}")

    print("\n--- Tests beendet ---")



