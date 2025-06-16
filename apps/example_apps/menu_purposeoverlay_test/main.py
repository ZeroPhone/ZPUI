from zpui_lib.apps import ZeroApp
from zpui_lib.ui import Menu
from zpui_lib.ui.overlays import PurposeOverlay

class MainMenu(ZeroApp):

    menu_name = "Main Menu"

    def on_start(self):
        self.m = Menu([["Hello"], ["Test"]], self.i, self.o)
        self.overlay = PurposeOverlay(purpose="Overlay test")
        self.overlay.apply_to(self.m)
        self.m.activate()
