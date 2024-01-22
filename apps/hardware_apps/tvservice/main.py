menu_name = "HDMI control"
#Some globals for LCS
callback = None
#Some globals for us
main_menu = None
i = None
o = None

from time import sleep

from ui import Menu, Printer, MenuExitException

from subprocess import check_output, CalledProcessError

import tvservice

def show_status():
    try:
        status = tvservice.status()
    except (IndexError, KeyError):
        Printer(["Unknown mode", "open GH issue"], i, o)
        return False
    mode = status['mode']
    status_menu_contents = [[["mode:", mode]]] #State is an element that's always there, let's see possible states
    if mode == 'UNKNOWN':
        Printer(["Unknown mode", "open GH issue"], i, o)
        return False
    if mode == 'NONE':
        Printer(["No video out", "active"], i, o)
        return False
    #Adding elements that are there both in HDMI and TV mode
    x, y = status["resolution"]
    refresh_rate = status["refresh_rate"]
    status_menu_contents.append([["Resolution&rate", "{}x{}, {}".format(x, y, refresh_rate)]])
    if mode == 'HDMI':
        group, mode, drive = status["gmd"]
        status_menu_contents.append([["GroupModeDrive", "{}, {}, {}".format(group, mode, drive)]])
    elif mode == 'TV':
        status_menu_contents.append([["TV mode: ", status["tv_mode"]]])
    status_menu_contents.append([["Ratio:", status["ratio"]]])
    status_menu_contents.append(["Show flags", lambda: Printer(status["flags"], i, o, skippable=True)])
    status_menu = Menu(status_menu_contents, i, o, "Tvservice status menu", entry_height=2)
    status_menu.activate()

def select_hdmi_mode():
    menu_contents = []
    try:
        current_group = tvservice.status()['gmd'][0]
    except (KeyError, IndexError):
        Printer(["Error, is HDMI", "enabled?"], i, o)
        return False
    modes = tvservice.get_modes(current_group)
    for mode in modes:
        width = mode["width"]
        height = mode["height"]
        rate = mode["rate"]
        menu_contents.append(["{}x{}@{}".format(width, height, rate), lambda x=mode: set_mode(x)])
    mode_menu = Menu(menu_contents, i, o, "Mode change menu")
    mode_menu.activate()

def set_mode(mode_desc):
    group, mode, drive = tvservice.status()['gmd']
    mode = mode_desc["code"]
    tvservice.set_mode(group, mode, drive)
    Printer(['Changed to', "{},{},{}".format(group, mode, drive)], i, o, skippable=True)
    status = tvservice.status()
    try:
        x, y = status["resolution"]
    except KeyError:
        Printer(["Can't get", "resolution!"], i, o, skippable=True)
    else:
        try:
            check_output(["fbset", "-depth", "8"])
            check_output(["fbset", "-g", x, y, x, y, "16"])
            check_output(["chvt", "1"]) #HAAAAAAAAAX - we need to switch VTs for changes to appear
            check_output(["chvt", "7"]) #This relies on the fact that GUI is mostly on VT7 and most people will want GUI resolutionto change.
            #TODO: Restart X... Maybe?
        except:
            Printer(["Refresh failed!", "Try Ctrl-Alt-F1", "and Ctrl-Alt-F7"], i, o, skippable=True)
        else:
            raise MenuExitException #Alright, post-resolution-change triggers executed, nothing to do here

def display_off():
    tvservice.display_off()
    Printer(['Disabled display'], i, o, skippable=True)

def display_on():
    tvservice.display_on()
    Printer(['Enabled display', 'with defaults'], i, o, skippable=True)
    status = tvservice.status()
    try:
        x, y = status["resolution"]
    except KeyError:
        Printer(["Can't get", "resolution!"], i, o, skippable=True)
    else:
        try:
            check_output(["fbset", "-depth", "8"])
            check_output(["fbset", "-g", x, y, x, y, "16"])
            check_output(["chvt", "1"]) #HAAAAAAAAAX - we need to switch VTs for changes to appear
            check_output(["chvt", "7"]) #This relies on the fact that GUI is mostly on VT7
        except:
            Printer(["Refresh failed!", "Try Ctrl-Alt-F1", "and Ctrl-Alt-F7"], i, o, skippable=True)
        else:
            pass #All successful.

def launch():
    try:
       status = tvservice.status()
    except OSError as e:
       if e.errno == 2:
           Printer(["Do you have", "tvservice?"], i, o, 3, skippable=True)
           return
       else:
           raise e
    else:
        main_menu_contents = [
        ["Status", show_status],
        ["Choose HDMI mode", select_hdmi_mode],
        ["Display on", display_on],
        ["Display off", display_off]]
        main_menu = Menu(main_menu_contents, i, o, "tvservice main menu")
        main_menu.activate()


def init_app(input, output):
    global callback, i, o
    i = input; o = output
    callback = launch
