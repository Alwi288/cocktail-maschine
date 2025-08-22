import os
import sys

# Ensure src package is importable as top-level modules
sys.path.append(os.path.abspath('src'))

import database_manager as db
import core_logic


def setup_module(module):
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'cocktails.db'))
    if os.path.exists(db_path):
        os.remove(db_path)
    db.initialize_database()
    db.test_ingredients()
    db.test_recipes()
    db.test_recipe_ingredients()
    db.test_pumps()


def test_image_paths_exist_in_db():
    recipes = db.get_all_recipes()
    assert recipes, "No recipes found in database"
    for recipe in recipes:
        image_path = recipe[3]
        assert image_path, f"image_path missing for {recipe[1]}"
        assert image_path.endswith('.png'), f"image_path must be .png for {recipe[1]}"


def test_core_logic_provides_image_paths():
    available = core_logic.get_available_recipes()
    assert available, "No available recipes returned"
    for recipe in available:
        image_path = recipe[3]
        assert image_path, f"image_path missing for {recipe[1]}"
        assert image_path.endswith('.png'), f"image_path must be .png for {recipe[1]}"
