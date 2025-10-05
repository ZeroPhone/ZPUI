menu_name = "Flashlight"

import os
from time import sleep

from zpui_lib.ui import Canvas, Menu, Checkbox, PrettyPrinter as Printer
from zpui_lib.helpers import ExitHelper, get_platform, read_or_create_config, local_path_gen, save_config_gen
from zpui_lib.actions import ContextSwitchAction as Action

zerophone_hw = False
try:
    from zerophone_hw import RGB_LED
except:
    pass
else:
    zerophone_hw = True

led = None
state = False
context = None
i = None; o = None

local_path = local_path_gen(__name__)

default_config = "disabled_lights: []"
config = read_or_create_config(local_path("config.yaml"), default_config, menu_name+" app")
save_config = save_config_gen(local_path("config.yaml"))

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
        context.register_action(Action("flashlight_toggle", c.request_switch, menu_name=get_state_message, description="Switching to the flashlight app"))
        context.set_provider("settings_flashlight", flashlight_settings)

def get_platform_lights():
    platform = get_platform()
    lights = ["screen"]
    if "beepy" in platform:
        #lights.append("beepy_backlight") # currently not implemented but will be
        lights.append("beepy_led")
    return lights

def flashlight_toggles():
    lights = get_platform_lights()
    contents = {light:True for light in lights}
    for light in config["disabled_lights"]:
        contents[light] = False
    cb_contents = []
    for name, state in contents.items():
        hr_name = name.replace("_", " ").capitalize()
        cb_contents.append([hr_name, name, state])
    cb = Checkbox(cb_contents, i, o, name="Flashlight app toggles setting")
    result = cb.activate()
    if result:
        for name, state in result.items():
            if not state:
                if name not in  config["disabled_lights"]:
                    config["disabled_lights"].append(name)
            elif state and name in config["disabled_lights"]: # enabled but included in disabled items, removing
                config["disabled_lights"].remove(name)
        save_config(config)

def flashlight_settings():
    return flashlight_toggles()

flashlight_settings.name = "Flashlight settings"

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
        if "beepy_led" not in config["disabled_lights"]:
            if new_state: # LED on
                write_beepy_led("led_red", 100)
                write_beepy_led("led_green", 100)
                write_beepy_led("led_blue", 100)
                write_beepy_led("led", 1)
            else:
                write_beepy_led("led", 0)

def callback():
    global state
    # check - are all possible lights disabled?
    lights = get_platform_lights()
    if all([light in config["disabled_lights"] for light in lights]):
        Printer("All available lights disabled!", i, o, 3)
        return
    # do we have a color screen? if so, block
    # first thing to do: toggle the LED
    state = not state
    set_led(state)
    # now, fill the canvas with white
    # damn, wish I could filter this out on the Memory LCD
    # if this can be filtered out, this would be the spot that callback() would stop executing in
    if "screen" not in config["disabled_lights"]:
        c = Canvas(o, interactive=True)
        if state: # new state
            c.clear(fill="white") # hardcoded as flashlight colour
        else:
            c.clear(fill="black")
    if state and "screen" not in config["disabled_lights"]:
        eh = ExitHelper(i, keys=["KEY_ENTER", "KEY_LEFT"]).start()
        while eh.do_run():
            sleep(0.1)
        last_key = eh.last_key
        if last_key == "KEY_ENTER":
            # flip the LED before exiting
            set_led(not state)
            state = not state
            c.clear(fill="white" if state else "black")
    # todo: if no external LED is supported, disable flashlight on exit
    # in the future, we could add KEY_RIGHT and use that for flashlight settings? would be fun maybe
