#!/usr/bin/python

from luma.lcd.device import ili9341

from output.output import OutputDevice
from output.drivers.luma_driver import LumaScreen


function_mock = lambda *a, **k: True
device_mock = type("ILI9341", (), {"mode":'1', "size":(320, 240), "display": function_mock, "hide": function_mock, "show": function_mock, "real":False})

class Screen(LumaScreen, OutputDevice):
    """An object that provides high-level functions for interaction with display. It contains all the high-level logic and exposes an interface for system and applications to use."""

    default_width = 320
    default_height = 240
    default_rotate = 0
    default_gpio_rst = 1 # beepis

    def init_display(self, **kwargs):
        """Initializes  controller. """
        self.rotate = kwargs.pop("rotate", self.default_rotate)
        try:
            self.device = ili9341(self.serial, width=self.width, height=self.height, rotate=self.rotate)
            self.device.real = True
        except:
            self.device = device_mock
        self.reattach_callback = self.reinit_display

    def reinit_display(self):
        try:
            self.device = ili9341(self.serial, width=self.width, height=self.height, rotate=self.rotate)
            self.device_mode = self.device.mode
            self.device.real = True
            self.device.show()
        except:
            self.device = device_mock
        else:
            self.display_image(self.current_image)
