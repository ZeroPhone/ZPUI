menu_name = "Shutdown&reboot"

from subprocess import call
from ui import Menu, DialogBox
from actions import FirstBootAction

context = None
def set_context(c):
    global context
    context = c
    context.register_firstboot_action(FirstBootAction("reboot_after_firstboot", reboot_after_firstboot, depends=["change_wifi_country"], not_on_emulator=True))

def shutdown():
    o.clear()
    o.display_data("Shutting down")
    call(['shutdown', '-h', 'now'])

def reboot():
    o.clear()
    o.display_data("Rebooting")
    call(['reboot'])

def reboot_after_firstboot():
    choice = DialogBox("ync", i, o, message="Reboot to apply changes?", name="Reboot app firstboot reboot dialog").activate()
    if not choice:
        return True
    o.clear()
    o.display_data("Rebooting")
    call(['reboot'])
    return True



#Some globals for LCS
main_menu = None
callback = None
#Some globals for us
i = None
o = None

main_menu_contents = [
["Shutdown", shutdown],
["Reboot", reboot],
["Exit", 'exit']
]

def init_app(input, output):
    global main_menu, callback, i, o
    i = input; o = output
    main_menu = Menu(main_menu_contents, i, o, "Shutdown menu")
    callback = main_menu.activate

