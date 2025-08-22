import sqlite3
from sqlite3 import Error
import yaml
import os
import logging
import datetime # Für Zeitstempel im PourLog benötigt

# --- Logging Setup ---
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DatabaseManager')
logger.setLevel(logging.DEBUG) # DEBUG für ausführliche Test-Logs
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)
# ---------------------

DATABASE_PATH = None
PUMP_COUNT = 8 # Feste Anzahl der Pumpen

# --- Config & Connection ---
def load_db_config():
    global DATABASE_PATH
    if DATABASE_PATH is None:
        # ... (Code unverändert von oben) ...
        script_dir = os.path.dirname(__file__)
        config_path = os.path.join(script_dir, '..', 'config', 'config.yaml')
        logger.debug(f"Lade DB-Konfiguration von: {config_path}")
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                if 'database_path' in config:
                    project_root = os.path.join(script_dir, '..')
                    DATABASE_PATH = os.path.join(project_root, config['database_path'])
                    logger.info(f"Datenbankpfad initialisiert: {DATABASE_PATH}")
                    db_dir = os.path.dirname(DATABASE_PATH)
                    if db_dir and not os.path.exists(db_dir):
                        logger.info(f"Erstelle Datenbank-Verzeichnis: {db_dir}")
                        os.makedirs(db_dir)
                    return True
                else:
                    logger.error("Konfigurationsdatei fehlt 'database_path'.")
                    return False
        except FileNotFoundError:
            logger.error(f"Konfigurationsdatei nicht gefunden: {config_path}")
            return False
        except Exception as e:
            logger.error(f"Fehler beim Laden der DB-Konfiguration: {e}")
            return False
    return DATABASE_PATH is not None

def create_connection():
    if not load_db_config():
         logger.error("Kann Datenbankpfad nicht laden. Verbindung nicht möglich.")
         return None
    conn = None
    try:
        # detect_types ist wichtig für TIMESTAMP
        conn = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.execute("PRAGMA foreign_keys = ON")
        logger.debug(f"Verbindung zu SQLite DB '{DATABASE_PATH}' hergestellt (Version: {sqlite3.sqlite_version}). Foreign Keys aktiviert.")
        return conn
    except Error as e:
        logger.error(f"Fehler beim Verbinden mit der Datenbank '{DATABASE_PATH}': {e}")
        return None

# --- Table Creation ---
def create_table(conn, create_table_sql):
    try:
        # ... (Code unverändert von oben) ...
        c = conn.cursor()
        c.execute(create_table_sql)
        logger.info(f"SQL ausgeführt (Tabelle erstellt/überprüft): {create_table_sql.split('(')[0]}...")
    except Error as e:
        logger.error(f"Fehler beim Erstellen der Tabelle: {e}")

def initialize_database():
    logger.info("Initialisiere Datenbank...")
    conn = create_connection()
    if conn is not None:
        # SQL Statements (alle 6 wie vorher)
        sql_create_ingredients_table = """ CREATE TABLE IF NOT EXISTS ingredients (ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE); """
        sql_create_pumps_table = """ CREATE TABLE IF NOT EXISTS pumps (pump_index INTEGER PRIMARY KEY, assigned_ingredient_id INTEGER, current_volume_ml REAL DEFAULT 0.0, calibration_ml_per_sec REAL DEFAULT 0.0, FOREIGN KEY (assigned_ingredient_id) REFERENCES ingredients (ingredient_id) ON DELETE SET NULL); """
        sql_create_recipes_table = """ CREATE TABLE IF NOT EXISTS recipes (recipe_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE, description TEXT, image_path TEXT, instructions TEXT); """
        sql_create_recipe_ingredients_table = """ CREATE TABLE IF NOT EXISTS recipe_ingredients (recipe_ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT, recipe_id INTEGER NOT NULL, ingredient_id INTEGER NOT NULL, amount REAL NOT NULL, unit TEXT DEFAULT 'ml', FOREIGN KEY (recipe_id) REFERENCES recipes (recipe_id) ON DELETE CASCADE, FOREIGN KEY (ingredient_id) REFERENCES ingredients (ingredient_id) ON DELETE CASCADE); """
        sql_create_settings_table = """ CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY COLLATE NOCASE, value TEXT); """
        sql_create_pour_log_table = """ CREATE TABLE IF NOT EXISTS pour_log (log_id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TIMESTAMP NOT NULL, recipe_id INTEGER, size_ml REAL, FOREIGN KEY (recipe_id) REFERENCES recipes (recipe_id) ON DELETE SET NULL); """

        # Tabellen erstellen
        create_table(conn, sql_create_ingredients_table)
        create_table(conn, sql_create_pumps_table)
        create_table(conn, sql_create_recipes_table)
        create_table(conn, sql_create_recipe_ingredients_table)
        create_table(conn, sql_create_settings_table)
        create_table(conn, sql_create_pour_log_table)

        # Initialisiere Pumpen-Einträge
        try:
            cur = conn.cursor()
            for i in range(PUMP_COUNT):
                cur.execute("INSERT OR IGNORE INTO pumps(pump_index) VALUES(?)", (i,))
            conn.commit()
            logger.info(f"Pumpen-Einträge 0 bis {PUMP_COUNT-1} sichergestellt.")
        except Error as e:
            logger.error(f"Fehler beim Initialisieren der Pumpen-Einträge: {e}")

        # Standardeinstellungen initialisieren
        try:
             c = conn.cursor()
             c.execute("SELECT COUNT(*) FROM settings")
             if c.fetchone()[0] == 0:
                 logger.info("Initialisiere Standardeinstellungen...")
                 # ... (Code unverändert von oben) ...
                 if load_db_config():
                    script_dir = os.path.dirname(__file__)
                    config_path = os.path.join(script_dir, '..', 'config', 'config.yaml')
                    try:
                        with open(config_path, 'r') as f:
                            config = yaml.safe_load(f)
                            if 'technician_pin' in config:
                                 c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('TechnicianPIN', config['technician_pin']))
                            if 'glass_sizes' in config and config['glass_sizes']:
                                 first_glass_name = list(config['glass_sizes'].keys())[0]
                                 c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('SelectedGlassSize', first_glass_name))
                            conn.commit()
                            logger.info("Standardeinstellungen erfolgreich initialisiert.")
                    except Exception as conf_e:
                         logger.error(f"Fehler beim Lesen der Config für Standardeinstellungen: {conf_e}")
        except Error as e:
             logger.error(f"Fehler beim Initialisieren der Standardeinstellungen: {e}")

        conn.close()
        logger.info("Datenbank-Initialisierung abgeschlossen. Verbindung geschlossen.")
    else:
        logger.error("Datenbank-Initialisierung fehlgeschlagen: Keine Verbindung.")


# ========== CRUD Ingredients ==========
# (unverändert)
def add_ingredient(name):
    # ...
    sql = ''' INSERT INTO ingredients(name) VALUES(?) '''
    conn = create_connection()
    if conn is None: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT ingredient_id FROM ingredients WHERE name = ? COLLATE NOCASE", (name,))
        existing = cur.fetchone()
        if existing:
            logger.warning(f"Zutat '{name}' existiert bereits mit ID {existing[0]}. Füge nicht erneut hinzu.")
            conn.close()
            return existing[0]
        cur.execute(sql, (name,))
        conn.commit()
        new_id = cur.lastrowid
        logger.info(f"Zutat '{name}' erfolgreich mit ID {new_id} hinzugefügt.")
        conn.close()
        return new_id
    except Error as e:
        logger.error(f"Fehler beim Hinzufügen der Zutat '{name}': {e}")
        conn.close()
        return None

def get_ingredient_by_id(ingredient_id):
    # ...
    conn = create_connection()
    if conn is None: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ingredients WHERE ingredient_id=?", (ingredient_id,))
        row = cur.fetchone()
        conn.close()
        logger.debug(f"get_ingredient_by_id({ingredient_id}) -> {row}")
        return row
    except Error as e:
        logger.error(f"Fehler beim Holen der Zutat mit ID {ingredient_id}: {e}")
        conn.close()
        return None

def get_ingredient_by_name(name):
    # ...
    conn = create_connection()
    if conn is None: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ingredients WHERE name=? COLLATE NOCASE", (name,))
        row = cur.fetchone()
        conn.close()
        logger.debug(f"get_ingredient_by_name({name}) -> {row}")
        return row
    except Error as e:
        logger.error(f"Fehler beim Holen der Zutat mit Namen '{name}': {e}")
        conn.close()
        return None

def get_all_ingredients():
    # ...
    conn = create_connection()
    if conn is None: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM ingredients ORDER BY name COLLATE NOCASE")
        rows = cur.fetchall()
        conn.close()
        logger.debug(f"get_all_ingredients() -> {len(rows)} Zutaten gefunden.")
        return rows
    except Error as e:
        logger.error(f"Fehler beim Holen aller Zutaten: {e}")
        conn.close()
        return []


# ========== CRUD Recipes ==========
# (unverändert)
def add_recipe(name, description=None, image_path=None, instructions=None):
    # ...
    sql = ''' INSERT INTO recipes(name, description, image_path, instructions)
              VALUES(?,?,?,?) '''
    conn = create_connection()
    if conn is None: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT recipe_id FROM recipes WHERE name = ? COLLATE NOCASE", (name,))
        existing = cur.fetchone()
        if existing:
            logger.warning(f"Rezept '{name}' existiert bereits mit ID {existing[0]}. Füge nicht erneut hinzu.")
            conn.close()
            return existing[0]
        cur.execute(sql, (name, description, image_path, instructions))
        conn.commit()
        new_id = cur.lastrowid
        logger.info(f"Rezept '{name}' erfolgreich mit ID {new_id} hinzugefügt.")
        conn.close()
        return new_id
    except Error as e:
        logger.error(f"Fehler beim Hinzufügen des Rezepts '{name}': {e}")
        conn.close()
        return None

def get_recipe_by_id(recipe_id):
    # ...
    conn = create_connection()
    if conn is None: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM recipes WHERE recipe_id=?", (recipe_id,))
        row = cur.fetchone()
        conn.close()
        logger.debug(f"get_recipe_by_id({recipe_id}) -> {row}")
        return row
    except Error as e:
        logger.error(f"Fehler beim Holen des Rezepts mit ID {recipe_id}: {e}")
        conn.close()
        return None

def get_recipe_by_name(name):
    # ...
    conn = create_connection()
    if conn is None: return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM recipes WHERE name=? COLLATE NOCASE", (name,))
        row = cur.fetchone()
        conn.close()
        logger.debug(f"get_recipe_by_name({name}) -> {row}")
        return row
    except Error as e:
        logger.error(f"Fehler beim Holen des Rezepts mit Namen '{name}': {e}")
        conn.close()
        return None

def get_all_recipes():
    # ...
    conn = create_connection()
    if conn is None: return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM recipes ORDER BY name COLLATE NOCASE")
        rows = cur.fetchall()
        conn.close()
        logger.debug(f"get_all_recipes() -> {len(rows)} Rezepte gefunden.")
        return rows
    except Error as e:
        logger.error(f"Fehler beim Holen aller Rezepte: {e}")
        conn.close()
        return []


# ========== Funktionen für RecipeIngredients ==========
# (unverändert)
def add_ingredient_to_recipe(recipe_id, ingredient_id, amount, unit='ml'):
    # ...
    sql = ''' INSERT INTO recipe_ingredients(recipe_id, ingredient_id, amount, unit)
              VALUES(?,?,?,?) '''
    conn = create_connection()
    if conn is None: return False
    try:
        cur = conn.cursor()
        cur.execute(sql, (recipe_id, ingredient_id, amount, unit))
        conn.commit()
        logger.info(f"Zutat ID {ingredient_id} ({amount}{unit}) zu Rezept ID {recipe_id} hinzugefügt.")
        conn.close()
        return True
    except Error as e:
        logger.error(f"Fehler beim Hinzufügen von Zutat ID {ingredient_id} zu Rezept ID {recipe_id}: {e}")
        conn.close()
        return False

def get_ingredients_for_recipe(recipe_id):
    # ...
    sql = """ SELECT i.name, ri.amount, ri.unit
              FROM recipe_ingredients ri
              JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
              WHERE ri.recipe_id = ?
              ORDER BY i.name COLLATE NOCASE """
    conn = create_connection()
    if conn is None: return []
    try:
        cur = conn.cursor()
        cur.execute(sql, (recipe_id,))
        rows = cur.fetchall()
        conn.close()
        logger.debug(f"get_ingredients_for_recipe({recipe_id}) -> {len(rows)} Zutaten gefunden.")
        return rows
    except Error as e:
        logger.error(f"Fehler beim Holen der Zutaten für Rezept ID {recipe_id}: {e}")
        conn.close()
        return []


# ========== CRUD Funktionen für Pumps ==========
# (unverändert)
def assign_ingredient_to_pump(pump_index, ingredient_id):
    # ...
    if not (0 <= pump_index < PUMP_COUNT):
         logger.error(f"Ungültiger Pumpenindex: {pump_index}")
         return False
    sql = """ UPDATE pumps SET assigned_ingredient_id = ? WHERE pump_index = ? """
    conn = create_connection()
    if conn is None: return False
    try:
        cur = conn.cursor()
        cur.execute(sql, (ingredient_id, pump_index))
        conn.commit()
        if ingredient_id:
             ing_info = get_ingredient_by_id(ingredient_id)
             ing_name = ing_info[1] if ing_info else "Unbekannte ID"
             logger.info(f"Pumpe {pump_index} wurde Zutat '{ing_name}' (ID: {ingredient_id}) zugewiesen.")
        else:
             logger.info(f"Zutat von Pumpe {pump_index} entfernt.")
        conn.close()
        return True
    except Error as e:
        logger.error(f"Fehler beim Zuweisen von Zutat ID {ingredient_id} zu Pumpe {pump_index}: {e}")
        conn.close()
        return False

def update_pump_volume(pump_index, volume_ml):
    # ...
    if not (0 <= pump_index < PUMP_COUNT):
         logger.error(f"Ungültiger Pumpenindex für Volumen-Update: {pump_index}")
         return False
    sql = """ UPDATE pumps SET current_volume_ml = ? WHERE pump_index = ? """
    conn = create_connection()
    if conn is None: return False
    try:
        cur = conn.cursor()
        cur.execute(sql, (volume_ml, pump_index))
        conn.commit()
        logger.info(f"Volumen für Pumpe {pump_index} auf {volume_ml:.2f}ml gesetzt.")
        conn.close()
        return True
    except Error as e:
        logger.error(f"Fehler beim Update des Volumens für Pumpe {pump_index}: {e}")
        conn.close()
        return False

def update_pump_calibration(pump_index, ml_per_sec):
    # ...
    if not (0 <= pump_index < PUMP_COUNT):
         logger.error(f"Ungültiger Pumpenindex für Kalibrierungs-Update: {pump_index}")
         return False
    sql = """ UPDATE pumps SET calibration_ml_per_sec = ? WHERE pump_index = ? """
    conn = create_connection()
    if conn is None: return False
    try:
        cur = conn.cursor()
        cur.execute(sql, (ml_per_sec, pump_index))
        conn.commit()
        logger.info(f"Kalibrierung für Pumpe {pump_index} auf {ml_per_sec:.2f}ml/sec gesetzt.")
        conn.close()
        return True
    except Error as e:
        logger.error(f"Fehler beim Update der Kalibrierung für Pumpe {pump_index}: {e}")
        conn.close()
        return False

def get_pump_info(pump_index):
    # ...
    if not (0 <= pump_index < PUMP_COUNT):
         logger.error(f"Ungültiger Pumpenindex für get_pump_info: {pump_index}")
         return None
    sql = """ SELECT p.pump_index, p.assigned_ingredient_id, i.name, p.current_volume_ml, p.calibration_ml_per_sec
              FROM pumps p
              LEFT JOIN ingredients i ON p.assigned_ingredient_id = i.ingredient_id
              WHERE p.pump_index = ? """
    conn = create_connection()
    if conn is None: return None
    try:
        cur = conn.cursor()
        cur.execute(sql, (pump_index,))
        row = cur.fetchone()
        conn.close()
        logger.debug(f"get_pump_info({pump_index}) -> {row}")
        return row
    except Error as e:
        logger.error(f"Fehler beim Holen der Infos für Pumpe {pump_index}: {e}")
        conn.close()
        return None

def get_all_pumps_info():
    # ...
    sql = """ SELECT p.pump_index, p.assigned_ingredient_id, i.name, p.current_volume_ml, p.calibration_ml_per_sec
              FROM pumps p
              LEFT JOIN ingredients i ON p.assigned_ingredient_id = i.ingredient_id
              ORDER BY p.pump_index """
    conn = create_connection()
    if conn is None: return []
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        logger.debug(f"get_all_pumps_info() -> {len(rows)} Pumpen-Infos gefunden.")
        return rows
    except Error as e:
        logger.error(f"Fehler beim Holen aller Pumpen-Infos: {e}")
        conn.close()
        return []


# ========== CRUD Funktionen für Settings ========== NEU

def get_setting(key, default=None):
    """ Holt einen Wert aus der Settings-Tabelle. """
    conn = create_connection()
    if conn is None: return default
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key=? COLLATE NOCASE", (key,))
        row = cur.fetchone()
        conn.close()
        if row:
            logger.debug(f"get_setting('{key}') -> '{row[0]}'")
            return row[0] # Gib den Wert zurück
        else:
            logger.debug(f"get_setting('{key}') -> Nicht gefunden, gebe Default '{default}' zurück.")
            return default # Gib Default zurück, wenn Schlüssel nicht existiert
    except Error as e:
        logger.error(f"Fehler beim Holen der Einstellung '{key}': {e}")
        conn.close()
        return default

def set_setting(key, value):
    """ Setzt oder aktualisiert einen Wert in der Settings-Tabelle. """
    # INSERT OR REPLACE: Fügt ein, wenn key neu; ersetzt, wenn key existiert
    sql = ''' INSERT OR REPLACE INTO settings(key, value) VALUES(?,?) '''
    conn = create_connection()
    if conn is None: return False
    try:
        cur = conn.cursor()
        cur.execute(sql, (key, value))
        conn.commit()
        logger.info(f"Einstellung '{key}' auf '{value}' gesetzt.")
        conn.close()
        return True
    except Error as e:
        logger.error(f"Fehler beim Setzen der Einstellung '{key}'='{value}': {e}")
        conn.close()
        return False


# ========== CRUD Funktionen für PourLog ========== NEU

def add_pour_log_entry(recipe_id, size_ml):
    """ Fügt einen Eintrag zum Pour-Log hinzu. """
    sql = ''' INSERT INTO pour_log(timestamp, recipe_id, size_ml) VALUES(?,?,?) '''
    conn = create_connection()
    if conn is None: return False
    try:
        now = datetime.datetime.now() # Aktueller Zeitstempel
        cur = conn.cursor()
        cur.execute(sql, (now, recipe_id, size_ml))
        conn.commit()
        log_id = cur.lastrowid
        logger.info(f"Pour Log Eintrag {log_id} hinzugefügt: Rezept ID {recipe_id}, Größe {size_ml}ml um {now}.")
        conn.close()
        return log_id
    except Error as e:
         # Foreign Key Error, falls recipe_id ungültig ist
        logger.error(f"Fehler beim Hinzufügen zum Pour Log (Rezept ID {recipe_id}): {e}")
        conn.close()
        return None

def get_pour_log(limit=50):
    """ Holt die letzten N Einträge aus dem Pour-Log. """
    # JOIN mit recipes, um den Rezeptnamen mitzuliefern
    sql = """ SELECT pl.log_id, pl.timestamp, pl.recipe_id, r.name, pl.size_ml
              FROM pour_log pl
              LEFT JOIN recipes r ON pl.recipe_id = r.recipe_id
              ORDER BY pl.timestamp DESC
              LIMIT ? """
    conn = create_connection()
    if conn is None: return []
    try:
        cur = conn.cursor()
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
        conn.close()
        logger.debug(f"get_pour_log(limit={limit}) -> {len(rows)} Einträge gefunden.")
        # Gibt Liste von Tupeln zurück [(log_id, time, r_id, r_name, size), ...]
        return rows
    except Error as e:
        logger.error(f"Fehler beim Holen des Pour Logs: {e}")
        conn.close()
        return []


# --- Code zum direkten Testen dieses Moduls ---
# (Funktionen zum Testen der einzelnen Teile)
def test_ingredients():
    # ... (unverändert) ...
    print("\n--- Teste Ingredient CRUD Funktionen ---")
    print("Füge Zutaten hinzu...")
    add_ingredient("Rum (weiss)")
    add_ingredient("Limetten Saft")
    add_ingredient("Cola")
    add_ingredient("Orangen Saft")
    add_ingredient("Wodka")
    add_ingredient("Cola") # Doppelt

    print("\nAlle Zutaten:")
    ingredients = get_all_ingredients()
    if ingredients:
        for ingredient in ingredients: print(f"  ID: {ingredient[0]}, Name: {ingredient[1]}")
    else: print("Keine Zutaten gefunden.")

def test_recipes():
    # ... (unverändert) ...
    print("\n--- Teste Recipe CRUD Funktionen ---")
    print("Füge Rezepte hinzu...")
    image_folder = os.path.join('images')
    add_recipe("Cuba Libre", "Ein Klassiker.", os.path.join(image_folder, "cuba_libre.png"), "Rum und Cola mischen, Limettensaft dazu.")
    add_recipe("Screwdriver", "Simpel und gut.", os.path.join(image_folder, "screwdriver.png"), "Wodka und Orangensaft.")
    add_recipe("Cuba Libre") # Doppelt

    print("\nAlle Rezepte:")
    recipes = get_all_recipes()
    if recipes:
        for recipe in recipes: print(f"  ID: {recipe[0]}, Name: {recipe[1]}, Bild: {recipe[3]}")
    else: print("Keine Rezepte gefunden.")

def test_recipe_ingredients():
    # ... (unverändert, prüft jetzt ob schon vorhanden) ...
    print("\n--- Teste RecipeIngredients Funktionen ---")
    rum = get_ingredient_by_name("Rum (weiss)")
    limette = get_ingredient_by_name("Limetten Saft")
    cola = get_ingredient_by_name("Cola")
    wodka = get_ingredient_by_name("Wodka")
    orange = get_ingredient_by_name("Orangen Saft")
    cuba_libre = get_recipe_by_name("Cuba Libre")
    screwdriver = get_recipe_by_name("Screwdriver")

    if not all([rum, limette, cola, wodka, orange, cuba_libre, screwdriver]):
        logger.error("Konnte nicht alle benötigten Zutaten/Rezepte für den RecipeIngredients Test finden!")
        return

    if not get_ingredients_for_recipe(cuba_libre[0]):
         print(f"Definiere Zutaten für '{cuba_libre[1]}' (ID: {cuba_libre[0]})")
         add_ingredient_to_recipe(cuba_libre[0], rum[0], 50)
         add_ingredient_to_recipe(cuba_libre[0], cola[0], 150)
         add_ingredient_to_recipe(cuba_libre[0], limette[0], 10)
    if not get_ingredients_for_recipe(screwdriver[0]):
         print(f"\nDefiniere Zutaten für '{screwdriver[1]}' (ID: {screwdriver[0]})")
         add_ingredient_to_recipe(screwdriver[0], wodka[0], 50)
         add_ingredient_to_recipe(screwdriver[0], orange[0], 150)

    print("\nZutaten für Cuba Libre:")
    ingredients_cl = get_ingredients_for_recipe(cuba_libre[0])
    if ingredients_cl:
        for ing in ingredients_cl: print(f"  - {ing[0]} ({ing[1]} {ing[2]})")
    else: print("  Keine Zutaten gefunden.")

def test_pumps():
    # ... (unverändert) ...
    print("\n--- Teste Pumps CRUD Funktionen ---")
    rum = get_ingredient_by_name("Rum (weiss)")
    cola = get_ingredient_by_name("Cola")
    limette = get_ingredient_by_name("Limetten Saft")

    if not all([rum, cola, limette]):
         logger.error("Konnte nicht alle benötigten Zutaten für den Pumpen-Test finden!")
         return

    print("Weise Zutaten zu Pumpen zu...")
    assign_ingredient_to_pump(0, rum[0])
    assign_ingredient_to_pump(1, cola[0])
    assign_ingredient_to_pump(2, limette[0])
    assign_ingredient_to_pump(7, None)

    print("\nAktualisiere Volumen und Kalibrierung...")
    update_pump_volume(0, 700.0)
    update_pump_calibration(0, 5.5)
    update_pump_volume(1, 1000.0)
    update_pump_calibration(1, 8.1)
    update_pump_volume(2, 250.0)
    update_pump_calibration(2, 4.0)

    print("\nInfos für alle Pumpen:")
    all_pumps = get_all_pumps_info()
    if all_pumps:
        for pump in all_pumps:
            ing_id = f"ID:{pump[1]}" if pump[1] is not None else "None"
            ing_name = pump[2] if pump[2] is not None else "----"
            volume = f"{pump[3]:.1f}ml" if pump[3] is not None else "?.?ml"
            calib = f"{pump[4]:.2f}ml/s" if pump[4] > 0 else "- ml/s"
            print(f"  Pumpe {pump[0]}: Zutat={ing_name} ({ing_id}), Vol={volume}, Calib={calib}")
    else:
        print("Keine Pumpeninfos gefunden.")

def test_settings(): # NEU
    print("\n--- Teste Settings CRUD Funktionen ---")
    pin_before = get_setting("TechnicianPIN", "FEHLER")
    size_before = get_setting("SelectedGlassSize", "FEHLER")
    non_existent = get_setting("NonExistentKey", "DefaultWert")
    print(f"Vorher: PIN='{pin_before}', Size='{size_before}', NonExistent='{non_existent}'")

    print("Ändere Einstellungen...")
    set_setting("TechnicianPIN", "9999")
    set_setting("SelectedGlassSize", "Large")
    set_setting("NewSetting", "TestValue")

    pin_after = get_setting("TechnicianPIN")
    size_after = get_setting("SelectedGlassSize")
    new_setting = get_setting("NewSetting")
    print(f"Nachher: PIN='{pin_after}', Size='{size_after}', NewSetting='{new_setting}'")

    # Zurücksetzen für nächste Läufe (optional)
    set_setting("TechnicianPIN", pin_before)
    set_setting("SelectedGlassSize", size_before)


def test_pour_log(): # NEU
    print("\n--- Teste PourLog Funktionen ---")
    # Hole Rezept IDs
    cuba_libre = get_recipe_by_name("Cuba Libre")
    screwdriver = get_recipe_by_name("Screwdriver")

    if not all([cuba_libre, screwdriver]):
        logger.error("Konnte Rezepte für PourLog Test nicht finden!")
        return

    print("Füge Log-Einträge hinzu...")
    log_id1 = add_pour_log_entry(cuba_libre[0], 200) # Cuba Libre, 200ml
    log_id2 = add_pour_log_entry(screwdriver[0], 250) # Screwdriver, 250ml
    log_id3 = add_pour_log_entry(cuba_libre[0], 150) # Cuba Libre, 150ml

    print("\nLetzte Log-Einträge (max 5):")
    log_entries = get_pour_log(limit=5)
    if log_entries:
        for entry in log_entries:
            # Zeitstempel formatieren für bessere Lesbarkeit
            ts = entry[1].strftime('%Y-%m-%d %H:%M:%S') if isinstance(entry[1], datetime.datetime) else entry[1]
            r_name = entry[3] if entry[3] else f"Unbekannt (ID:{entry[2]})"
            size = f"{entry[4]:.0f}ml" if entry[4] else "?ml"
            print(f"  ID: {entry[0]}, Zeit: {ts}, Rezept: '{r_name}', Größe: {size}")
    else:
        print("Keine Log-Einträge gefunden.")


if __name__ == '__main__':
    print("--- Teste Database Manager Modul (FINAL) ---")
    logger.setLevel(logging.DEBUG) # Sicherstellen, dass DEBUG aktiv ist
    initialize_database()
    test_ingredients()
    test_recipes()
    test_recipe_ingredients()
    test_pumps()
    test_settings() # NEU
    test_pour_log() # NEU
    print("\n--- Alle Tests beendet ---")
