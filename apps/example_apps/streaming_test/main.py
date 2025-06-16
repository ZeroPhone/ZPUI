menu_name = "Refresher app"

from zpui_lib.ui import Refresher, PrettyPrinter

counter = 0
keys_called = []

def process_key(key, *args):
    global counter, keys_called
    if len(keys_called) >= o.rows:
        keys_called = keys_called[1:]
    keys_called.append([counter, key])
    counter += 1
    ltk = [k for c, k in keys_called][-3:]
    if len(ltk) >= 3 and ltk[0]==ltk[1]==ltk[2]:
        refresher.deactivate()
    else:
        refresher.refresh() #Makes changes appear faster

def get_keys():
    return ["{}:{}".format(num, key) for num, key in keys_called]

refresher = None
i = None #Input device
o = None #Output device

def callback():
    global refresher, keys_called
    keys_called = []
    i.set_streaming(process_key)
    refresher = Refresher(get_keys, i, o, 1, name="Key monitor")
    refresher.keymap.pop("KEY_LEFT") #Removing deactivate callback to show KEY_LEFT
    PrettyPrinter("To exit this app, press the same key 3 times", i, o)
    refresher.activate()
    i.remove_streaming()
