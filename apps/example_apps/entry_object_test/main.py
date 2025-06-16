from __future__ import print_function

menu_name = "Entry object testing"

from zpui_lib.ui import Menu, Entry

# Some globals for us
i = None # Input device
o = None # Output device

def callback():
    contents = [Entry("Hello1", cb=lambda: print("1")),
                Entry("Hello2", cb=lambda: print("2"), cb2=lambda: print("3"))]
    Menu(contents, i, o, "Entry object test menu").activate()
