menu_name = "Refresher app"

from datetime import datetime

from zpui_lib.ui import Refresher

counter = 0

def count():
    global counter
    counter += 1
    return ["Counter is", str(counter)]

def show_time():
    now = datetime.now()
    return [now.strftime("%H:%M:%S").center(o.cols), now.strftime("%Y-%m-%d").center(o.cols)]

#Callback global for ZPUI. It gets called when application is activated in the main menu
callback = None

#Some globals for us
i = None #Input device
o = None #Output device

def init_app(input, output):
    global callback, i, o
    i = input; o = output #Getting references to output and input device objects and saving them as globals
    time_refresher = Refresher(show_time, i, o, 1, name="Timer")
    counter_refresher = Refresher(count, i, o, 1, keymap={"KEY_KPENTER":time_refresher.activate, "KEY_RIGHT":"change_interval"}, name="Counter")
    callback = counter_refresher.activate

