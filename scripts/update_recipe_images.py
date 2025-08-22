#!/usr/bin/env python3
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src import database_manager

IMAGE_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets', 'images')
RELATIVE_PREFIX = os.path.join('assets', 'images')

def slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

def update_image_paths():
    conn = database_manager.create_connection()
    if conn is None:
        print("Keine Verbindung zur Datenbank.")
        return
    cur = conn.cursor()
    cur.execute("SELECT recipe_id, name FROM recipes")
    recipes = cur.fetchall()
    for recipe_id, name in recipes:
        slug = slugify(name)
        updated = False
        for ext in ('.jpg', '.png'):
            filename = slug + ext
            full_path = os.path.join(IMAGE_DIR, filename)
            if os.path.exists(full_path):
                rel_path = os.path.join(RELATIVE_PREFIX, filename)
                cur.execute("UPDATE recipes SET image_path=? WHERE recipe_id=?", (rel_path, recipe_id))
                print(f"{name}: {rel_path}")
                updated = True
                break
        if not updated:
            print(f"Kein Bild für Rezept '{name}' gefunden.")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    update_image_paths()
