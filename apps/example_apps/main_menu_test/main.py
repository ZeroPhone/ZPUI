import os

from zpui_lib.apps import ZeroApp
from zpui_lib.ui import GridMenu, Entry, GridMenuLabelOverlay, GridMenuSidebarOverlay, open_image

def func_test(x):
    print(x)

class MainMenu(ZeroApp):

    menu_name = "Main Menu"

    def sidebar_cb(self, c, ui_el, coords):
        width = coords.right-coords.left
        height = coords.bottom-coords.top
        cw = coords.left+width/2
        ch= coords.top+height/2
        c.centered_text("Hello", cw=cw, ch=ch)

    def on_start(self):
        dir = "resources/"
        icons = [f for f in os.listdir(dir) if f.endswith(".png")]
        icon_paths = [[f, os.path.join(dir, f)] for f in icons]
        grid_contents = [Entry(f.rsplit('.', 1)[0].capitalize(), icon=open_image(p), cb=lambda x=f: func_test(x)) \
                                for f,p in icon_paths]
        self.gm = GridMenu(grid_contents, self.i, self.o, entry_width=32, draw_lines=False)
        self.overlay1 = GridMenuLabelOverlay()
        self.overlay1.apply_to(self.gm)
        self.overlay2 = GridMenuSidebarOverlay(self.sidebar_cb)
        self.overlay2.apply_to(self.gm)
        self.gm.activate()
