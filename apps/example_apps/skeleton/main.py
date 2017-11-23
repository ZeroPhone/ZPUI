from subprocess import call

from input.input import InputListener
from ui.menu import Menu
from ui.printer import Printer

menu_name = "Skeleton app"  # App name as seen in main menu while using the system
InputListener()

def call_internal():
    Printer(["Calling internal", "command"], i, o, 1)
    print("Success")


def call_external():
    Printer(["Calling external", "command"], i, o, 1)
    call(['echo', 'Success'])


# Callback global for ZPUI. It gets called when application is activated in the main menu
callback = None

i = None  # Input device
o = None  # Output device


def init_app(input: InputListener, output: float) -> None:
    global callback, i, o
    i, o = input, output  # Getting references to output and input device objects and saving them as globals
    main_menu_contents = [
        ["Internal command", call_internal],
        ["External command", call_external],
        ["Exit", 'exit']]
    main_menu = Menu(main_menu_contents, i, o, "Skeleton app menu")
    callback = main_menu.activate
