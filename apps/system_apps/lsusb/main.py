menu_name = "USB devices"

from ui import Menu, Printer, PrettyPrinter, ellipsize

from zpui_lib.libs import lsusb

i = None
o = None

def init_app(input, output):
    global i, o
    i = input; o = output

def callback():
    menu_contents = []
    try:
        usb_devices = lsusb.lsusb()
    except OSError:
        PrettyPrinter("Do you have lsusb?", i, o, 2)
        return False
    for bus, dev, vid_pid, name in usb_devices:
        name = name if name else "[Unknown]"
        ell_name = ellipsize(name, o.cols)
        info = "{}\n{}".format(vid_pid, name)
        menu_contents.append([["D{},B{},{}".format(bus, dev, vid_pid), ell_name], lambda x=info: PrettyPrinter(x, i, o, skippable=True)])
    Menu(menu_contents, i, o, entry_height=2).activate()
