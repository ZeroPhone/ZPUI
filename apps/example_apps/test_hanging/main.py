menu_name = "Test hangup"

from zpui_lib.ui import Printer
from time import sleep

i = None
o = None

def callback():
    Printer("Hangup", None, o, 0)
    while True:
        sleep(1)
