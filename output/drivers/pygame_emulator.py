"""
Pygame-based emulator for the ZeroPhone OLED screen
Allows development of sofware without ZeroPhone hardware,
e.g. on a laptop with a USB keyboard.
"""

import logging
from threading import Event
from time import sleep

from luma.core.render import canvas

import emulator
from output.output import OutputDevice


class Screen(OutputDevice):
    """
    Screen is an important class; all display is done by this class.
    On program start main.py invokes output.py which looks up
    an output driver and the output driver creates a Screen instance.

    Screen provides high-level functions for interaction with display.
    It contains all the high-level logic and
    exposes an interface for system and applications to use.

    menu.py makes callbacks to display_data() and setCursor()
    methods in this class
    """

    def __init__(self, **kwargs):
        """ Sets variables for high-level functions."""
        self.char_width = 6
        self.char_height = 8
        self.cols = 128 / self.char_width
        self.rows = 64 / self.char_height

        self.init_display(**kwargs)

    def init_display(self):
        """
        Creates subprocess of a of pygame emulator device
        """

        logging.debug('Creating emulator instance')
        self.emulator = emulator.get_emulator()

    def __getattr__(self, name):
        return getattr(self.emulator, name)

    #def display_data(self, *args):
    #    """Displays data on display.
    #    called from menu.py refresh() so don't remove this method
    #    This function does the actual work of printing things to display.
    #    ``*args`` is a list of strings,
    #              where each string corresponds to a row of the display,
    #              starting with 0.
    #              Note:  the emulator does not support passing tuples, lists
    #              or anything except comma delimited simple strings as args.
    #    """
    #    self.emulator.display_data(*args)

    #def setCursor(self, row, col):
    #    """
    #    Called from menu.py refresh() so don't remove this method
    #    Set current input cursor to ``row`` and ``column`` specified """
    #    self.emulator.setCursor(row, col)

    #def noCursor(self):
    #    """ Turns the box cursor off """
    #    self.emulator.noCursor()

    #def cursor(self):
    #    """ Turns the box cursor on """
    #    self.emulator.cursor()
