from __future__ import print_function

menu_name = "Help overlay test"

from ui import Listbox, HelpOverlay
from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "info")
i = None
o = None

def callback():
    listbox_contents = [
    ["NumberAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", 101],
    ["String", "stringstring"],
    ["Tuple", (1, 2, 3)]]
    lb = Listbox(listbox_contents, i, o)
    HelpOverlay(lambda: print("Halp plz")).apply_to(lb)
    lb.activate()

def init_app(input, output):
    global i, o
    i = input; o = output
