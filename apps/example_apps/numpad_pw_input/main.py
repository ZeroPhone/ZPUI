from zpui_lib.helpers import setup_logger
from zpui_lib.ui import NumpadPasswordInput as PassInput

menu_name = "Password input app"

logger = setup_logger(__name__, "info")

# Some globals for us
i = None # Input device
o = None # Output device

# Callback for ZPUI. It gets called when application is activated in the main menu
def callback():
    char_input = PassInput(i, o, message="Input characters")
    logger.info(repr(char_input.activate()))

