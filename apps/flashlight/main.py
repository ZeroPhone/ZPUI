menu_name = "Flashlight"

from time import sleep

from ui import Canvas
from zpui_lib.helpers import ExitHelper
from zpui_lib.helpers.env import get_platform

zerophone_hw = False
try:
    from zerophone_hw import RGB_LED
except:
    pass
else:
    zerophone_hw = True

from actions import BackgroundAction as Action

global i, o

led = None
state = False
context = None

def can_load():
    # maybe in the future we can check if the screen has backlit output, and if any LEDs are available
    return True

# we don't even need this function right now, really
"""
def init_app(input, output):
    global i, o, led
    i = input; o = output
    if zerophone_hw:
        try:
            led = RGB_LED()
        except PermissionError:
            pass # expected rn honestly; TODO make processing of this error nicer
"""

def set_context(c):
    global context
    if can_load() == True:
        context = c
        context.register_action(Action("flashlight_toggle", callback, menu_name=get_state_message, description="Flashlight toggle"))

def get_state_message():
    if state:
        return "Flashlight on"
    else:
        return "Flashlight off"

def write_beepy_led(path, param, fw_path="/sys/firmware/beepy/"):
    with open(os.path.join(fw_path, path), "w") as f:
        f.write(str(param))

def set_led(new_state):
    """
    # do we have the ZeroPhone LED available? No way to know rn, I forgor =(
    if "zerophone" in get_platform():
    if False: #if zerophone_hw:
        if not state:
            led.set_color("white")
            state = True
        else:
            led.set_color("none")
            state = False
    """
    # do we have the Beepy LED available?
    if "beepy" in get_platform():
        if state: # LED on
            write_beepy_led("led_red", 100)
            write_beepy_led("led_green", 100)
            write_beepy_led("led_blue", 100)
            write_beepy_led("led", 1)
        else:
            write_beepy_led("led", 0)

def callback():
    global state
    # do we have a color screen? if so, block
    # first thing to do: toggle the LED
    set_led(not state)
    state = not state
    # now, fill the canvas with white
    # damn, wish I could filter this out on the Memory LCD
    # if this can be filtered out, this would be the spot that callback() would stop executing in
    c = Canvas(o, interactive=True)
    if state: # new state
        c.clear(fill="white") # hardcoded as flashlight colour
    else:
        c.clear(fill="black")
    eh = ExitHelper(i, keys=["KEY_ENTER", "KEY_LEFT"]).start()
    while eh.do_run():
        sleep(0.1)
    last_key = eh.last_key
    if last_key == "KEY_ENTER":
        set_led(not state)
        state = not state
        c.clear(fill="white" if state else "black")
    # in the future, we could add KEY_RIGHT and use that for flashlight settings owo
