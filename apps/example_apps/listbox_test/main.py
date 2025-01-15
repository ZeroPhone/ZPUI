

from zpui_lib.helpers import setup_logger

menu_name = "Listbox test" #App name as seen in main menu while using the system

from ui import Listbox

logger = setup_logger(__name__, "info")
#Some globals for us
i = None #Input device
o = None #Output device

def callback():
    listbox_contents = [
    ["Number", 101],
    ["String", "stringstring"],
    ["Tuple", (1, 2, 3)]]
    logger.info(Listbox(listbox_contents, i, o).activate())

def init_app(input, output):
    global i, o
    i = input; o = output #Getting references to output and input device objects and saving them as globals

