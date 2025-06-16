menu_name = "File browser"

from zpui_lib.ui import PathPicker, Printer
import os

callback = None

i = None
o = None

def print_path(path):
    if os.path.isdir(path):
        Printer("Dir: {}".format(path), i, o, 5)
    elif os.path.isfile(path):
        Printer("File: {}".format(path), i, o, 5)
    else:
        Printer("WTF: {}".format(path), i, o, 5) # ;-P

def callback():
    #"File options" menu yet to be added
    path_picker = PathPicker("/", i, o, callback=print_path)
    path_picker.activate()
