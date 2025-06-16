from __future__ import print_function

menu_name = "Menu arrow testing"

from zpui_lib.ui import Menu

# Some globals for us
i = None # Input device
o = None # Output device

def callback():
    contents = [["Arrow test", lambda: print("Enter"), lambda: print("Right")]]
    Menu(contents, i, o, "Menu arrow test menu").activate()
