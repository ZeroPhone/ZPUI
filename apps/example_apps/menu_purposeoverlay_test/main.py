from apps import ZeroApp
from ui import Menu

from ui.overlays import PurposeOverlay

class MainMenu(ZeroApp):

	menu_name = "Main Menu"

	def on_start(self):
		self.m = Menu([["Hello"], ["Test"]], self.i, self.o)
		self.overlay = PurposeOverlay(purpose="Overlay test")
                self.overlay.apply_to(self.m)
		self.m.activate()
