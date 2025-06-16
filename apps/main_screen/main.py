import os
from datetime import datetime
from threading import Event
from cProfile import Profile
#from cProfile import runcall as profile

from mock import Mock
from zpui_lib.apps import ZeroApp
from zpui_lib.ui import Menu, PrettyPrinter, Canvas

from zerophone_hw import is_charging
from PIL import ImageFont

from __main__ import input_processor, cm # TODO: dirty hack, to be removed

class App(ZeroApp):

    menu_name = "Main screen"

    def __init__(self, *args, **kwargs):
        ZeroApp.__init__(self, *args, **kwargs)
        #input_processor.set_global_callback("KEY_HANGUP", self.switch_to_self)

    #def switch_to_self(self):
    #    cm.switch_to_context("apps/main_screen")

    def on_start(self, *args, **kwargs):
        screen = MainScreen([], self.i, self.o, "Main screen")
        screen.activate()
        screen.p.print_stats(2)

class MainScreen(Menu):
    is_numbered = False

    def set_view(self, config):
        self.view = Mock()

    def idle_loop(self):
        Menu.idle_loop(self)
        self.refresh()

    #def switch_to_main_menu(self):
    #    cm.switch_to_context("main")

    #def switch_to_stopwatch(self):
    #    cm.switch_to_context("stopwatch")

    #def generate_keymap(self):
    #    keymap = {"KEY_F1":self.switch_to_main_menu, "KEY_F2":self.switch_to_stopwatch}
    #    Menu.generate_keymap(self)
    #    self.keymap.update(keymap)

    def validate_contents(self, contents):
        self.p = Profile()

    def process_contents(self):
        pass

    def draw_battery_icon(self, c):
        c.rectangle(("-20", 0, "-2", 7))
        c.rectangle(("-16", 0, "-2", 7), fill="white")
        c.rectangle(("-22", 1, "-20", 6), fill="white")
        if is_charging():
            c.text("Ch", ("-15", -2))

    def draw_network_icon(self, c):
        c.line((3, 1, 3, 6))
        c.line((1, 1, 5, 1))
        c.point(((1, 2), (5, 2)))
        offset = 7
        for x in reversed(range(6)):
            c.line((x*2+offset, 6-x, x*2+offset, 6))

    def refresh(self):
        now = datetime.now()
        hhmm = now.strftime("%H:%M")
        ss = now.strftime("%S")
        ddmmyy = now.strftime("%d%m%y")
        c = Canvas(self.o)
        #c.line((0, 8, c.width, 8), fill="white")
        c.text(hhmm, (5, 8), font=("Fixedsys62.ttf", 32))
        c.text(ss, (87, 23))
        c.text(ddmmyy, (90, 12))
        c.text("0 notifications", (10, 39))
        self.draw_battery_icon(c)
        self.draw_network_icon(c)
        image = c.get_image()
        self.p.runcall( self.o.display_image, image )
