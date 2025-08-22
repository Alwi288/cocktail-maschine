from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.properties import NumericProperty, StringProperty


class CocktailImageButton(ButtonBehavior, Image):
    """Image-based button that stores a recipe ID."""
    recipe_id = NumericProperty()
    text = StringProperty("")

    def __init__(self, recipe_id, **kwargs):
        super().__init__(**kwargs)
        self.recipe_id = recipe_id
