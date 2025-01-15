

from zpui_lib.helpers import setup_logger

menu_name = "Skeleton app"  # App name as seen in main menu while using the system

from subprocess import call
from time import sleep

from ui import Menu, Printer

logger = setup_logger(__name__, "info")

def call_internal():
    Printer(["Calling internal", "command"], i, o, 1)
    logger.info("Success")

def call_external():
    Printer(["Calling external", "command"], i, o, 1)
    call(['echo', 'Success'])

#Callback global for ZPUI. It gets called when application is activated in the main menu
callback = None

i = None #Input device
o = None #Output device

def init_app(input, output):
    global callback, i, o
    i = input;
    o = output  # Getting references to output and input device objects and saving them as globals
    main_menu_contents = [
    ["Internal command", call_internal],
    ["External command", call_external],
    ["Exit", 'exit']]
    main_menu = Menu(main_menu_contents, i, o, "Skeleton app menu")
    callback = main_menu.activate

