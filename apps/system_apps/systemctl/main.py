menu_name = "Systemctl"

config_filename = "config.json"
default_config = '{"allowed_types":["service","target"], "pinned_units":["zpui.service"]}'

callback = None
i = None
o = None

from time import sleep

from ui import Menu, Printer, PrettyPrinter, Checkbox, MenuExitException

try:
    from libs import systemctl
except ImportError as e:
    try: # Are we missing gi.repository?
        import gi.repository
    except (ImportError, ModuleNotFoundError): # Yep, that's the case - let's disable the library so we can notify the user
        print("gi module not found!")
        systemctl = None
    else: # Nope, it's something else - re-raising
        raise e

from zpui_lib.helpers import read_or_create_config, write_config, local_path_gen
local_path = local_path_gen(__name__)
config_path = local_path(config_filename)
config = read_or_create_config(config_path, default_config, menu_name+" app")

#Migrating config in case it's preserved from older app versions
if "pinned_units" not in config:
    config["pinned_units"] = ["zpui.service"]
    write_config(config, config_path)

def change_filters():
    global config
    all_types = [
    ["Slices", 'slice'],
    ["Sockets", 'socket'],
    ["Services", 'service'],
    ["Automounts", 'automount'],
    ["Mounts", 'mount'],
    ["Timers", 'timer'],
    ["Paths", 'path'],
    ["Devices", 'device'],
    ["Scopes", 'scope'],
    ["Targets", 'target']]
    checkbox_contents = []
    for type in all_types:
        checkbox_contents.append([type[0], type[1], type[1] in config["allowed_types"]])
    states = Checkbox(checkbox_contents, i, o, final_button_name="Save").activate()
    if states is None: return None
    config["allowed_types"] = [state for state in states if states[state]]
    write_config(config, config_path)

def all_units():
    menu_contents = []
    units = systemctl.list_units()
    for unit in units:
        menu_contents.append([unit["name"], lambda x=unit: unit_menu(x)])
    Menu(menu_contents, i, o, "Systemctl: all unit list menu").activate()

def pinned_units():
    menu_contents = []
    units = systemctl.list_units("name", config["pinned_units"])
    for unit in units:
        menu_contents.append([unit["name"], lambda x=unit["name"]: unit_menu({"name":x}, in_pinned=True)])
    Menu(menu_contents, i, o, "Pinned unit list menu").activate()

def filtered_units():
    menu_contents = []
    units = systemctl.list_units("unit_type", config["allowed_types"])
    for unit in units:
        menu_contents.append([unit["name"], lambda x=unit: unit_menu(x)])
    Menu(menu_contents, i, o, "Systemctl: filtered unit list menu").activate()

def unit_menu(unit, in_pinned=False):
    name = unit["name"]
    unit_menu_contents = [
    ["Full name", lambda x=name: Printer(x, i, o)],
    ["Start unit", lambda x=name: start_unit(x)],
    ["Stop unit", lambda x=name: stop_unit(x)],
    ["Restart unit", lambda x=name: restart_unit(x)],
    ["Reload unit", lambda x=name: reload_unit(x)],
    ["Enable unit", lambda x=name: enable_unit(x)],
    ["Disable unit", lambda x=name: disable_unit(x)]]
    if in_pinned:
        unit_menu_contents.append(["Unpin unit", lambda x=name: unpin_unit(x)])
    else:
        unit_menu_contents.append(["Pin unit", lambda x=name: pin_unit(x)])
    Menu(unit_menu_contents, i, o, "{} unit menu".format(name)).activate()

def pin_unit(name):
    global config
    config["pinned_units"].append(name)
    write_config(config, config_path)
    PrettyPrinter("Pinned unit {}".format(name), i, o, 1)

def unpin_unit(name):
    global config
    if name in config["pinned_units"]:
        config["pinned_units"].remove(name)
        write_config(config, config_path)
        PrettyPrinter("Unpinned unit {}".format(name), i, o, 1)
    else:
        PrettyPrinter("Error: unit {} not pinned!".format(name), i, o, 1)

#Those functions might benefit from being turned into one generic function, I think

def start_unit(name):
    status = systemctl.action_unit("start", name)
    if status:
        PrettyPrinter("Started unit {}".format(name), i, o, 1)
    else:
        PrettyPrinter("Can't start {}".format(name), i, o, 1)
    raise MenuExitException

def stop_unit(name):
    status = systemctl.action_unit("stop", name)
    if status:
        PrettyPrinter("Stopped unit {}".format(name), i, o, 1)
    else:
        PrettyPrinter("Can't stop {}".format(name), i, o, 1)
    raise MenuExitException

def restart_unit(name):
    status = systemctl.action_unit("restart", name)
    if status:
        PrettyPrinter("Restarted unit {}".format(name), i, o, 1)
    else:
        PrettyPrinter("Can't restart {}".format(name), i, o, 1)
    raise MenuExitException

def reload_unit(name):
    status = systemctl.action_unit("reload", name)
    if status:
        PrettyPrinter("Reloaded unit {}".format(name), i, o, 1)
    else:
        PrettyPrinter("Can't reload {}".format(name), i, o, 1)
    raise MenuExitException

def enable_unit(name):
    status = systemctl.action_unit("enable", name)
    if status:
        PrettyPrinter("Enabled unit {}".format(name), i, o, 1)
    else:
        PrettyPrinter("Can't enable {}".format(name), i, o, 1)
    raise MenuExitException

def disable_unit(name):
    status = systemctl.action_unit("disable", name)
    if status:
        PrettyPrinter("Disabled unit {}".format(name), i, o, 1)
    else:
        PrettyPrinter("Can't disable {}".format(name), i, o, 1)
    raise MenuExitException


def callback():
    if systemctl is None:
       PrettyPrinter("python-gi not found! Please install it using 'apt-get install python-gi' ", i, o, 5)
       return
    try:
       systemctl.list_units()
    except OSError as e:
       if e.errno == 2:
           PrettyPrinter("Do you use systemctl?", i, o, 3, skippable=True)
           return
       else:
           raise e
    main_menu_contents = [
    ["Pinned units", pinned_units],
    ["Units (filtered)", filtered_units],
    ["All units", all_units],
    ["Change filters", change_filters]]
    main_menu = Menu(main_menu_contents, i, o, "systemctl main menu")
    main_menu.activate()

def init_app(input, output):
    global i, o
    i = input; o = output
