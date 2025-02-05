from apps import ZeroApp
from ui import Menu

from ui.overlays import SpinnerOverlay

class MainMenu(ZeroApp):

	menu_name = "Main Menu"

	def on_start(self):
		self.m = Menu([], self.i, self.o)
		self.overlay = SpinnerOverlay()
		def test_func(x):
			self.overlay.set_state(self.m, not self.overlay.get_state(self.m))
		menu_contents = [[str(i), lambda x=i: test_func(x)] for i in range(16)]
                self.overlay.apply_to(self.m)
                self.m.set_contents(menu_contents)
		self.m.activate()
