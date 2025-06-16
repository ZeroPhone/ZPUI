menu_name = "Scrolling test"

i = None
o = None

from zpui_lib.ui import Menu, Printer, Listbox, PathPicker

def callback():
    lb_contents = [["Very long listbox option name", 1], ["Even longer option name", 2]]
    lb=Listbox(lb_contents, i, o, "Scrolling test listbox")
    pp=PathPicker('/', i, o)
    main_menu_contents = [
    ["Command with very long name", lb.activate],
    ["Command with an even longer name", pp.activate],
    ["Exit", 'exit']]
    main_menu = Menu(main_menu_contents, i, o, "Scrolling test menu")
    main_menu.activate()

