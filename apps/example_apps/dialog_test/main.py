from zpui_lib.helpers import setup_logger
from zpui_lib.ui import DialogBox, Canvas

menu_name = "DialogBox test" # App name as seen in main menu while using the system

logger = setup_logger(__name__, "info")
# Some globals for us
i = None # Input device
o = None # Output device
context = None

def set_context(c):
    global context
    context = c

def callback():
    c = Canvas(o)
    c.line((0, o.height, o.width, 0))
    c.line((0, 0, o.width, o.height))
    #c.display()
    db = DialogBox('ync', i, o, message="It's working?")
    db.context = context
    logger.info(db.activate())
    logger.info((DialogBox('yyy', i, o, message="Isn't it beautiful?").activate()))
    logger.info((DialogBox([["Yes", True], ["Absolutely", True]], i, o, message="Do you like it").activate()))
