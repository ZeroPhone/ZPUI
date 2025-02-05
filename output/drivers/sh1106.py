#!/usr/bin/python

from luma.oled.device import sh1106

from output.output import OutputDevice
from output.drivers.luma_driver import LumaScreen


class Screen(LumaScreen, OutputDevice):
    """An object that provides high-level functions for interaction with display. It contains all the high-level logic and exposes an interface for system and applications to use."""

    default_rotate = 0

    def init_display(self, **kwargs):
        """Initializes SH1106 controller. """
        self.rotate = kwargs.pop("rotate", self.default_rotate)
        self.device = sh1106(self.serial, width=self.width, height=self.height, rotate=self.rotate)
