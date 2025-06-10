# test_kivy.py
from kivy.app import App
from kivy.uix.label import Label
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MinimalTest')

logger.info("Starte minimale Kivy App...")

class MinimalApp(App):
    def build(self):
        logger.info("MinimalApp build() wird aufgerufen...")
        try:
             widget = Label(text='Hello Kivy - Minimal Test!')
             logger.info("Label erstellt.")
             return widget
        except Exception as e:
             logger.exception(f"Fehler im build(): {e}")
             raise

if __name__ == '__main__':
    logger.info("Starte App Ausführung...")
    try:
        MinimalApp().run()
        logger.info("App erfolgreich beendet.")
    except RecursionError as re:
         logger.error(">>> RecursionError aufgetreten!")
         import sys
         logger.error(f"Rekursionstiefe erreicht: {sys.getrecursionlimit()}")
    except Exception as e:
        logger.exception(f">>> Unerwarteter Fehler beim Ausführen der MinimalApp: {e}")
    logger.info("Minimaler Test beendet.")

