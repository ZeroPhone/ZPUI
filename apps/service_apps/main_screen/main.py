import os
from datetime import datetime
from threading import Event
from mock import Mock

from zpui_lib.apps import ZeroApp
from zpui_lib.ui import Menu, PrettyPrinter, Refresher, Canvas, FunctionOverlay

from PIL import ImageFont

import menu_markup

class App(ZeroApp):

    menu_name = "Main screen"

    def __init__(self, *args, **kwargs):
        ZeroApp.__init__(self, *args, **kwargs)
        menu_markup.setup_canvas(self.o)
        self.zm = menu_markup.ZoneManager(self.i, self.o, menu_markup.markup,
                                     menu_markup.zones)
        #self.fo = FunctionOverlay(["deactivate", "deactivate"], labels=["Exit", "Tools"], wrap_view=False)
        self.screen = Refresher(self.get_image, self.i, self.o, name="Main screen")
        #self.fo.apply_to(self.screen)

    def get_image(self):
        self.zm.update()
        image = self.zm.get_image()
        #image = self.fo.modify_image_if_needed(self.screen, image)
        return image

    def set_context(self, c):
        self.context = c

    def on_start(self, *args, **kwargs):
        self.screen.activate()
