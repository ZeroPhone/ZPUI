menu_name = "Flashlight"

zerophone_hw = False
try:
    from zerophone_hw import RGB_LED
except:
    pass
from actions import BackgroundAction as Action

led = None
state = False
context = None

def can_load():
    # currently the app won't work with anything other than zerophone.
    # if you ask me, it also needs to fill the screen with white (decent flashlight supplement imo)
    return False, "app mothballed until its code is updated"

def init_app(i, o):
    global led
    if zerophone_hw:
        try:
            led = RGB_LED()
        except PermissionError:
            pass # expected rn honestly; TODO make processing of this error nicer

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

def callback():
    global state
    if not state:
        led.set_color("white")
        state = True
    else:
        led.set_color("none")
        state = False
