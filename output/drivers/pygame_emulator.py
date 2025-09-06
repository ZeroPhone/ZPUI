"""
Pygame-based emulator for the ZeroPhone OLED screen
Allows development of sofware without ZeroPhone hardware,
e.g. on a laptop with a USB keyboard.
"""

import emulator
from output.output import OutputDevice

from zpui_lib.helpers import setup_logger
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

        self.init_display(**kwargs)
        self.cols = kwargs.get("width", 128) // self.char_width
        self.rows = kwargs.get("height", 64) // self.char_height

    def init_display(self, **kwargs):
        """
        Creates subprocess of a of pygame emulator device
        """

        logger.debug('Creating emulator instance')
        self.emulator = emulator.get_emulator(**kwargs)

    def suspend(self):
        logger.info("Suspended emulator output (does not do anything)")
        self.suspended = True

    def unsuspend(self):
        logger.info("Suspended emulator output (does not do anything)")
        self.suspended = False

    def __getattr__(self, name):
        return getattr(self.emulator, name)
