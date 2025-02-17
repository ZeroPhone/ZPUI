from apps import ZeroApp
from ui import GridMenu

from ui.overlays import GridMenuNavOverlay

def func_test(x):
    print(x)

class MainMenu(ZeroApp):

    menu_name = "Main Menu"

    def on_start(self):
        grid_contents = [[str(i), lambda x=i: func_test(x)] for i in range(16)]

        self.gm = GridMenu(grid_contents, self.i, self.o)
        self.overlay = GridMenuNavOverlay()
        self.overlay.apply_to(self.gm)
        self.gm.activate()
