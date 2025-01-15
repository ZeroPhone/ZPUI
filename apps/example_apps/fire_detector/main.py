menu_name = "Flame detector"

from RPi import GPIO
import sys
import os

from zpui_lib.helpers import ExitHelper
from ui import GraphicsPrinter

local_path = lambda x: os.path.join( os.path.dirname(sys.modules[__name__].__file__), x )

i = None; o = None

def init_app(input, output):
    global i, o
    i = input; o = output

def callback():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.IN)
    eh = ExitHelper(i).start()
    while eh.do_run():
        state = GPIO.input(18)
        if state:
            GraphicsPrinter(local_path("no_fire.png"), None, o, 0.1)
        else:
            GraphicsPrinter(local_path("fire.png"), None, o, 0.1)
