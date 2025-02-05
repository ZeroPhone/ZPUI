menu_name = "MOCP control"

import shlex

from subprocess import call, CalledProcessError
from ui import Menu, Printer, DialogBox, IntegerAdjustInput, IntegerAdjustInputOverlay
from helpers import read_or_create_config, local_path_gen, save_config_gen

i = None
o = None

default_config = '{"command":"mocp", "seek_amount":60}' #has to be a string
config_filename = "config.json"

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


#MOCP commands
def mocp_command(*command, **options):
    try:
        mocp = config["command"]
        mocp = shlex.split(mocp) if not isinstance(mocp, list) else mocp
        return call(mocp + list(command))
    except (IOError, CalledProcessError):
        #We shouldn't print anything to the screen if called from a non-maskable callback
        silent = options.get("silent", False)
        if not silent:
            Printer(["Oops", "Is mocp there?"], i, o, 1)

def mocp_toggle_play():
    mocp_command("-G")

def mocp_next(silent=False):
    mocp_command("-f", silent=silent)

def mocp_prev(silent=False):
    mocp_command("-r", silent=silent)

def mocp_seek(sign, amount=None, silent=False):
    amount = config["seek_amount"] if not amount else amount
    mocp_command('--seek', "{}{}".format(sign, amount), silent=silent)

def mocp_seek_ui(sign, silent=False):
    amount = get_seek_amount()
    if amount:
        mocp_command('--seek', "{}{}".format(sign, amount), silent=silent)

def get_seek_amount(message="Amount:", start=10):
    return get_ia(start, i, o, message=message, min=0, name="MOCP app seek adjust").activate()

def option_switch_dialog(option):
    answer = DialogBox([["On", 'o'], ["Off", 'u'], ["Toggle", "t"]], i, o, message=option.capitalize()+":", name="MOCP {} option control dialog".format(option)).activate()
    if answer: mocp_switch_option(answer, option)

def mocp_switch_option(switch_type, option):
    mocp_command("-{}".format(switch_type), option)

shuffle_dialog = lambda: option_switch_dialog("shuffle")
repeat_dialog = lambda: option_switch_dialog("repeat")
autonext_dialog = lambda: option_switch_dialog("autonext")
mocp_seek_autof = lambda: mocp_seek("+")
mocp_seek_autob = lambda: mocp_seek("-")
mocp_seek_ui_f = lambda: mocp_seek_ui("+")
mocp_seek_ui_b = lambda: mocp_seek_ui("-")

def change_default_seek():
    amount = get_seek_amount(message="Default amount:", start=config["default_seek"])
    if amount:
        config["default_seek"] = amount
        save_config(config)

def settings():
    mc = [["Seek amount", change_default_seek]]
    Menu(mc, i, o, name="MOCP settings menu").activate()

main_menu_contents = [
["Toggle play/pause", mocp_toggle_play],
["Next song", mocp_next],
["Previous song", mocp_prev],
["Seek forwards", mocp_seek_autof, mocp_seek_ui_f],
["Seek backwards", mocp_seek_autob, mocp_seek_ui_b],
["Shuffle", shuffle_dialog],
["Repeat", repeat_dialog],
["Autonext", autonext_dialog],
["Settings", settings]
]

def set_global_callbacks():
    import __main__ #HHHHHAAAAAAAAAAAXXXX
    __main__.input_processor.set_global_callback("KEY_PROG1", mocp_next)
    __main__.input_processor.set_global_callback("KEY_CAMERA", mocp_prev)

def init_app(input, output):
    global i, o
    i = input; o = output
    set_global_callbacks()

def callback():
    Menu(main_menu_contents, i, o, "MOCP menu").activate()
