#!/usr/bin/python

from luma_driver import LumaScreen
from luma.oled.device import sh1106

from output.output import OutputDevice


class Screen(LumaScreen, OutputDevice):
    """An object that provides high-level functions for interaction with display. It contains all the high-level logic and exposes an interface for system and applications to use."""

    def init_display(self, autoscroll=False, **kwargs):
        """Initializes SH1106 controller. """
        self.device = sh1106(self.serial, width=128, height=64)
