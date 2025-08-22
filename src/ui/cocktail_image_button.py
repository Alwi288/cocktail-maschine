from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import NumericProperty


class CocktailImageButton(ButtonBehavior, Image):
    """Button that displays a cocktail image and stores a recipe id."""

    recipe_id = NumericProperty()
