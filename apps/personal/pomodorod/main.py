menu_name = "Pomodoro"

i = None
o = None

from time import sleep

from zpui_lib.ui import Menu, MenuExitException, Printer, IntegerAdjustInput, Refresher, DialogBox

from utils import RPCClient, RPCCommError
server = RPCClient('localhost', 4515)

def e_wr(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RPCCommError:
            Printer(["Can't connect", "to pomodorod!"], i, o, 1)
    return wrapper

def status_refresher_data():
    try:
        status_str = server.get_status()
    except RPCCommError:
        return ["Can't connect", "to pomodorod!"]
    else:
        return status_str

def callback():
    keymap = {"KEY_ENTER":pomodoro_options_menu}
    refresher = Refresher(status_refresher_data, i, o, 1, keymap, "Pomodoro monitor")
    refresher.activate()

def start_monitoring():
    server.start_work()
    raise MenuExitException

def start_break():
    server.start_break()
    raise MenuExitException

def stop_monitoring():
    server.break_work()
    raise MenuExitException

def ack_notification():
    server.acknowledge_notification()
    raise MenuExitException

def pomodoro_options_menu():
    menu_contents = [
    ["Acknowledge", e_wr(ack_notification)],
    ["Start", e_wr(start_monitoring)],
    ["Start break", e_wr(start_break)],
    ["Stop", e_wr(stop_monitoring)]]
    Menu(menu_contents, i, o, "Pomodoro options menu").activate()

def init_app(input, output):
    global i, o
    i = input; o = output
