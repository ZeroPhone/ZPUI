

from zpui_lib.helpers import setup_logger

menu_name = "DialogBox test" #App name as seen in main menu while using the system

from ui import DialogBox

logger = setup_logger(__name__, "info")
#Some globals for us
i = None #Input device
o = None #Output device

def callback():
    logger.info(DialogBox('ync', i, o, message="It's working?").activate())
    logger.info((DialogBox('yyy', i, o, message="Isn't it beautiful?").activate()))
    logger.info((DialogBox([["Yes", True], ["Absolutely", True]], i, o, message="Do you like it").activate()))

def init_app(input, output):
    global i, o
    i = input; o = output #Getting references to output and input device objects and saving them as globals

