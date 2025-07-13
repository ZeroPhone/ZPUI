menu_name = "Volume control"

config_filename = "config.json"
default_config = '{"card":0, "channel":"PCM", "adjust_amount":1, "adjust_type":"dB"}'

i = None
o = None
callback = None

from zpui_lib.helpers import read_or_create_config, write_config, local_path_gen
local_path = local_path_gen(__name__)
config_path = local_path(config_filename)
config = read_or_create_config(config_path, default_config, menu_name+" app")

import os
from subprocess import call, check_output

from zpui_lib.ui import Menu, IntegerAdjustInput, Listbox, ellipsize

#amixer commands
def amixer_command(command):
    with open(os.devnull, "w") as f:
        return call(['amixer'] + list(command), stdout=f)

def amixer_get_channels():
    controls = []
    output = check_output(['amixer', '-c', str(config["card"])])
    if isinstance(output, bytes): output = output.decode("ascii")
    for line in output.split('\n'):
        if 'mixer control' in line:
            controls.append(line.split("'")[1])
    return controls

def amixer_sset(sset_value):
    return amixer_command(["-c", str(config["card"]), "--", "sset", config["channel"], sset_value])

def get_adjust_value():
    return str(config["adjust_amount"])+config["adjust_type"]

def plus_volume():
    return amixer_sset(get_adjust_value()+'+')

def minus_volume():
    return amixer_sset(get_adjust_value()+'-')

def toggle_mute():
    return amixer_sset("toggle")

def settings_menu():
    menu_contents = [
    #["Select card", select_card],
    ["Select channel", select_channel],
    ["Adjust type", select_adjust_type],
    ["Adjust amount", change_adjust_amount]]
    Menu(menu_contents, i, o, "Settings menu").activate()

def select_card():
    #TODO get a list of all cards
    global config
    contents = []
    cards = [] 
    for card in cards:
        contents.append([ellipsize(card["name"], o.cols), card["id"]])
    card_id = Listbox(contents, i, o, "Card selection listbox").activate()
    if card_id is None:
        return False
    config["card"] = card_id
    write_config(config, config_path)

def select_channel():
    global config
    contents = []
    channels = amixer_get_channels()
    for channel in channels:
        contents.append([ellipsize(channel, o.cols), channel])
    channel = Listbox(contents, i, o, "Channel selection listbox").activate()
    if channel is None:
        return False
    config["channel"] = channel
    write_config(config, config_path)

def select_adjust_type():
    global config
    contents = [
    ["Percent", '%'],
    ["Decibels", 'dB'],
    ["HW value", '']]
    adjust_type = Listbox(contents, i, o, "Adjust selection listbox").activate()
    if adjust_type is None:
        return False
    config["adjust_type"] = adjust_type
    write_config(config, config_path)

def change_adjust_amount():
    global config
    value = IntegerAdjustInput(config['adjust_amount'], i, o, message="Adjust amount", interval=1).activate()
    if value is None:
        return False
    config["adjust_amount"] = value
    write_config(config, config_path)

def set_global_callbacks():
    import __main__ #HHHHHAAAAAAAAAAAXXXX
    __main__.zpui.input_processor.set_global_callback("KEY_VOLUMEUP", plus_volume)
    __main__.zpui.input_processor.set_global_callback("KEY_VOLUMEDOWN", minus_volume)

def init_app(input, output):
    global i, o, callback
    i = input; o = output
    set_global_callbacks()
    main_menu_contents = [ 
    ["Increase volume", plus_volume],
    ["Decrease volume", minus_volume],
    ["Toggle mute", toggle_mute],
    ["Settings", settings_menu]]
    callback = Menu(main_menu_contents, i, o, "Volume menu").activate

