menu_name = "Spinner"

from ui import Throbber
from helpers import ExitHelper

i = None
o = None

def init_app(input, output):
    global i, o
    i = input; o = output

class InputlessThrobber(Throbber):
    def configure_input(self):
        pass

def callback():
    eh = ExitHelper(i)
    th = InputlessThrobber(i, o, message="Idle spinner")
    eh.set_callback(th.stop)
    eh.start()
    th.activate()
