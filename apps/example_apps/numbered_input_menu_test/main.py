# coding=utf-8


from apps.zero_app import ZeroApp
from zpui_lib.helpers import setup_logger
from ui import NumberedMenu
import random

logger = setup_logger(__name__, "info")
class NumberedInputTestApp(ZeroApp):

    def __init__(self, i, o):
        super(NumberedInputTestApp, self).__init__(i, o)
        self.n_menu = None
        self.menu_name = "Numbered Input Menu"
        hellos = ["hello", "hello again", "ditto", "same"]
        self.main_menu_contents = [ [hellos[i%4],
                                    lambda x=i: self.print_hello(x, hellos[x%4])]
                                     for i in range(16) ]

    @staticmethod
    def print_hello(index, hello):
        logger.info("{} {}".format(index, hello))

    def on_start(self):
        self.n_menu = NumberedMenu(
            self.main_menu_contents,
            self.i,
            self.o,
            self.menu_name,
            prepend_numbers=True,
            input_delay=1)
        self.n_menu.activate()
