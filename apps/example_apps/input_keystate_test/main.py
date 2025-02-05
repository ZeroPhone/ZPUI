menu_name = "Input keystate test app"

from ui import Refresher, PrettyPrinter
from helpers import cb_needs_key_state, KEY_PRESSED, KEY_RELEASED, KEY_HELD

human_readable_state = {KEY_PRESSED:"down", KEY_HELD:"hold", KEY_RELEASED:"up"}

last_key_state = [None, None]

refresher = None
i = None #Input device
o = None #Output device

@cb_needs_key_state
def record_key_state(key, state):
    global last_key_state
    last_key_state = key, human_readable_state.get(state, None)
    refresher.refresh()

def show_key_state():
    return "{}:{}".format(*last_key_state)

def init_app(input, output):
    global i, o
    i = input; o = output

def callback():
    global refresher
    i.set_streaming(record_key_state)
    refresher = Refresher(show_key_state, i, o, 0.1, name="Key monitor")
    refresher.activate()
    i.remove_streaming()
