menu_name = "Volume control"

config_filename = "config.json"
default_config = '{"card":0, "channel":"Master", "adjust_amount":5, "adjust_type":"%"}'

i = None
o = None
callback = None

from helpers import read_config, write_config

import os,sys
current_module_path = os.path.dirname(sys.modules[__name__].__file__)

config_path = os.path.join(current_module_path, config_filename)

try:
    config = read_config(config_path)
except (ValueError, IOError): #damn braces
    print("Volume app: broken config, restoring with defaults...")
    with open(config_path, "w") as f:
        f.write(default_config)
    config = read_config(config_path)

from subprocess import call, check_output

from ui import Menu, IntegerAdjustInput, Listbox, ellipsize

#amixer commands
def amixer_command(command):
    return call(['amixer'] + list(command))

def amixer_get_channels():
    controls = []
    output = check_output(['amixer', '-c', str(config["card"])])
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
    return call(['pactl', 'set-sink-mute', '@DEFAULT_SINK@', 'toggle'])

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

def init_app(input, output):
    global i, o, callback
    i = input; o = output
    i.set_nonmaskable_callback("KEY_VOLUMEUP", plus_volume)
    i.set_nonmaskable_callback("KEY_VOLUMEDOWN", minus_volume)
    main_menu_contents = [ 
    ["Increase volume", plus_volume],
    ["Decrease volume", minus_volume],
    ["Toggle mute", toggle_mute],
    ["Settings", settings_menu]]
    callback = Menu(main_menu_contents, i, o, "Volume menu").activate

