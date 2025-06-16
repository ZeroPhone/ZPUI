from zpui_lib.ui import CharArrowKeysInput as Input
from zpui_lib.helpers import setup_logger

menu_name = "Char input app"

logger = setup_logger(__name__, "info")

# Some globals for us
i = None # Input device
o = None # Output device

# Callback for ZPUI. It gets called when application is activated in the main menu
def callback():
    char_input = Input(i, o, initial_value = "password")
    logger.info(repr(char_input.activate()))
