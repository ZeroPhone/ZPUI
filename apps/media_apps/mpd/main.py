menu_name = "MPD control (mpc)"

import os
import shlex
from subprocess import call, CalledProcessError

from zpui_lib.ui import Menu, PrettyPrinter as Printer, DialogBox, IntegerAdjustInput, IntegerAdjustInputOverlay, UniversalInput
from zpui_lib.helpers import read_or_create_config, local_path_gen, save_config_gen, setup_logger

i = None
o = None

logger = setup_logger(__name__, "info")

default_config = """command: mpc
seek_amount: 60"""
config_filename = "config.yaml"

local_path = local_path_gen(__name__)
config = read_or_create_config(local_path(config_filename), default_config, menu_name+" app")
save_config = save_config_gen(local_path(config_filename))

# TODO: replace 'silent' calls with context.is_active() checks, so that we can then expose
# actions to ZPUI

iaio = IntegerAdjustInputOverlay()

def get_ia(*args, **kwargs):
    ia = IntegerAdjustInput(*args, **kwargs)
    iaio.apply_to(ia)
    return ia


#mpc commands
def mpc_command(*command, **options):
    host = config.get("mpd_host", None)
    port = config.get("mpd_port", None)
    env = {}
    if host != None and host != "":
        env["MPD_HOST"] = host
    if port != None and port != 0:
        env["MPD_PORT"] = port
    try:
        mpc = config["command"]
        mpc = shlex.split(mpc) if not isinstance(mpc, list) else mpc
        cmd = mpc + list(command)
        logger.debug(f"Calling {repr(cmd)} with env {repr(env)}")
        return call(cmd, env=env)
    except (IOError, CalledProcessError):
        #We shouldn't print anything to the screen if called from a non-maskable callback
        silent = options.get("silent", False)
        if not silent:
            Printer("Oops, is mpc there?", i, o, 1)

def mpc_toggle_play():
    mpc_command("toggle")

def mpc_next(silent=False):
    mpc_command("next", silent=silent)

def mpc_prev(silent=False):
    mpc_command("prev", silent=silent)

def mpc_seek(sign, amount=None, silent=False):
    amount = config["seek_amount"] if not amount else amount
    mpc_command('seek', "{}{}".format(sign, amount), silent=silent)

def mpc_seek_ui(sign, silent=False):
    amount = get_seek_amount()
    if amount:
        mpc_command('seek', "{}{}".format(sign, amount), silent=silent)

def get_seek_amount(message="Amount:", start=10):
    return get_ia(start, i, o, message=message, min=0, name="MPC app seek adjust").activate()

def option_switch_dialog(option, options):
    option_list = options.split('/')
    option_list_db = [[opt.capitalize(), opt] for opt in option_list]
    answer = DialogBox(option_list_db, i, o, message=option.capitalize()+":", name="mpc {} option control dialog".format(option)).activate()
    if answer: mpc_switch_option(option, answer)

def mpc_switch_option(switch_type, option):
    mpc_command(switch_type, option)

shuffle_dialog = lambda: option_switch_dialog("random", options="on/off")
repeat_dialog = lambda: option_switch_dialog("repeat", options="on/off")
single_dialog = lambda: option_switch_dialog("single", options="on/once/off")
mpc_seek_autof = lambda: mpc_seek("+")
mpc_seek_autob = lambda: mpc_seek("-")
mpc_seek_ui_f = lambda: mpc_seek_ui("+")
mpc_seek_ui_b = lambda: mpc_seek_ui("-")

def change_seek_amount():
    amount = get_seek_amount(message="Default amount:", start=config["seek_amount"])
    if amount:
        config["seek_amount"] = amount
        save_config(config)

def change_default_host():
    current_value = config.get("mpd_host", "")
    host = UniversalInput(i, o, message="MPD host/file: (empty to clear)", value=current_value, name="MPC app host picker input").activate()
    if host != None: # input not cancelled?
        if host.startswith("/") and not os.path.exists(host):
            Printer("File {host} does not exist!", i, o, 3)
        # saving anyway
        if host == "":
            if "mpd_host" in config: config.remove("mpd_host")
        else:
            config["mpd_host"] = host
        save_config(config)

def change_default_port():
    current_value = str(config.get("mpd_port", ""))
    port = UniversalInput(i, o, message="MPD port/file: (0 to clear)", value=current_value, name="MPC app port picker input").activate()
    if port != None: # input not cancelled?
        if port == "0":
            if "mpd_port" in config: config.remove("mpd_port")
            save_config(config)
        elif port.isdigit():
            config["mpd_port"] = int(port)
            save_config(config)
        else:
            PrettyPrinter(f"Port '{port}' not a number!", i, o, 3)

def settings():
    mc = [
        ["Seek amount", change_seek_amount],
        ["Host", change_default_host],
        ["Port", change_default_port],
    ]
    Menu(mc, i, o, name="mpc settings menu").activate()

main_menu_contents = [
  ["Toggle play/pause", mpc_toggle_play],
  ["Next song", mpc_next],
  ["Previous song", mpc_prev],
  ["Seek forwards", mpc_seek_autof, mpc_seek_ui_f],
  ["Seek backwards", mpc_seek_autob, mpc_seek_ui_b],
  ["Shuffle", shuffle_dialog],
  ["Repeat", repeat_dialog],
  ["Single", single_dialog],
  ["Settings", settings]
]

def set_global_callbacks(zpui):
    zpui.input_processor.set_global_callback("KEY_PROG1", mpc_next)
    zpui.input_processor.set_global_callback("KEY_CAMERA", mpc_prev)

def set_context(c):
    zpui = c.request_zpui()
    if zpui:
        set_global_callbacks(zpui)

def callback():
    Menu(main_menu_contents, i, o, "MPC app main menu").activate()
