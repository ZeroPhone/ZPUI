from zpui_lib.apps import ZeroApp
from zpui_lib.ui import GridMenu

def func_test(x):
	print(x)

class MainMenu(ZeroApp):

	menu_name = "Main Menu"

	def on_start(self):
		grid_contents = [[str(i), lambda x=i: func_test(x)] for i in range(16)]

		self.gm = GridMenu(grid_contents, self.i, self.o)
		self.gm.activate()
