menu_name = "Shutdown&reboot"

from time import sleep
from subprocess import call

from zpui_lib.ui import Menu, DialogBox, LoadingIndicator
from zpui_lib.actions import FirstBootAction
from zpui_lib.helpers import ExitHelper

# Auto-set by ZPUI
i = None
o = None

context = None

def set_context(c):
    global context
    context = c
    context.register_firstboot_action(FirstBootAction("reboot_after_firstboot", reboot_after_firstboot, depends=["change_wifi_country"], not_on_emulator=True))

def shutdown():
    li = LoadingIndicator(i, o, message="Shutting down")
    li.run_in_background()
    call(['shutdown', '-h', 'now'])
    eh = ExitHelper(i, cb=li.stop).start()
    while eh.do_run():
        sleep(1)

def reboot():
    li = LoadingIndicator(i, o, message="Rebooting")
    li.run_in_background()
    call(['reboot'])
    eh = ExitHelper(i, cb=li.stop).start()
    while eh.do_run():
        sleep(1)

def reboot_after_firstboot():
    choice = DialogBox("ync", i, o, message="Reboot to apply changes?", name="Reboot app firstboot reboot dialog").activate()
    if not choice:
        return True
    o.clear()
    o.display_data("Rebooting")
    call(['reboot'])
    return True

def callback():
    contents = [
      ["Shutdown", shutdown],
      ["Reboot", reboot],
      ["Exit", 'exit']
    ]

    Menu(contents, i, o, "Shutdown menu").activate()

