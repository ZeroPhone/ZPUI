menu_name = "Spinner"

from zpui_lib.ui import Throbber
from zpui_lib.helpers import ExitHelper

i = None
o = None

class InputlessThrobber(Throbber):
    def configure_input(self):
        pass

def callback():
    eh = ExitHelper(i)
    th = InputlessThrobber(i, o, message="Idle spinner")
    eh.set_callback(th.stop)
    eh.start()
    th.activate()
