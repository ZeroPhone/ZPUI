from zpui_lib.helpers import setup_logger
from zpui_lib.ui import IntegerInDecrementInput as Input

menu_name = "Number input app"

logger = setup_logger(__name__, "info")

i = None #Input device
o = None #Output device

#Callback for ZPUI. It gets called when application is activated in the main menu
def callback():
    number_input = Input(0, i, o)
    logger.info(number_input.activate())
