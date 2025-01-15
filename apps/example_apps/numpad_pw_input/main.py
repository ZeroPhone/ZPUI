from zpui_lib.helpers import setup_logger

menu_name = "Password input app"

from ui import NumpadPasswordInput as PassInput

logger = setup_logger(__name__, "info")

#Some globals for us
i = None #Input device
o = None #Output device

#Callback for ZPUI. It gets called when application is activated in the main menu
def callback():
    char_input = PassInput(i, o, message="Input characters")
    logger.info(repr(char_input.activate()))

def init_app(input, output):
    global i, o
    i = input; o = output #Getting references to output and input device objects and saving them as globals

