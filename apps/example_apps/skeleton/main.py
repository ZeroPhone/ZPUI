from zpui_lib.helpers import setup_logger
from zpui_lib.ui import Menu, Printer

menu_name = "Skeleton app"  # App name as seen in main menu while using the system

from subprocess import call
from time import sleep

logger = setup_logger(__name__, "info")

i = None #Input device
o = None #Output device

def call_internal():
    Printer(["Calling internal", "command"], i, o, 1)
    logger.info("Success")

def call_external():
    Printer(["Calling external", "command"], i, o, 1)
    call(['echo', 'Success'])

#Callback global for ZPUI. It gets called when application is activated in the main menu
def callback():
    main_menu_contents = [
    ["Internal command", call_internal],
    ["External command", call_external],
    ["Exit", 'exit']]
    main_menu = Menu(main_menu_contents, i, o, "Skeleton app menu")
    main_menu.activate()
