"""
Pygame-based emulator for the ZeroPhone OLED screen
Allows development of sofware without ZeroPhone hardware,
e.g. on a laptop with a USB keyboard.
"""

import emulator
from output.output import OutputDevice

from helpers import setup_logger
logger = setup_logger(__name__, "info")

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
        self.cols = 128 // self.char_width
        self.rows = 64 // self.char_height

        self.init_display(**kwargs)

    def init_display(self):
        """
        Creates subprocess of a of pygame emulator device
        """

        logger.debug('Creating emulator instance')
        self.emulator = emulator.get_emulator()

    def __getattr__(self, name):
        return getattr(self.emulator, name)
