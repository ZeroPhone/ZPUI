menu_name = "Return to console"

import os
from time import sleep

from zpui_lib.ui import Canvas
from zpui_lib.helpers import ExitHelper, get_platform
from zpui_lib.actions import ContextSwitchAction as Action

context = None
i = None; o = None

def can_load():
    if "beepy" in get_platform() or "emulator" in get_platform():
        return True
    return False, "Minimizing ZPUI is currently not supported on platforms other than Beepy"

def set_context(c):
    global context
    if can_load() == True:
        context = c
        context.register_action(Action("minimize_zpui", c.request_switch, menu_name="Minimize ZPUI (console)", description="Put ZPUI into background so console can be accessed"))

def callback():
    from __main__ import zpui
    zpui.suspend()
