#!/usr/bin/python

from luma.oled.device import sh1106

from output.output import OutputDevice
from output.drivers.luma_driver import LumaScreen


function_mock = lambda *a, **k: True
device_mock = type("SH1106", (), {"mode":'1', "size":(128, 64), "display": function_mock, "hide": function_mock, "show": function_mock, "real":False})

class Screen(LumaScreen, OutputDevice):
    """An object that provides high-level functions for interaction with display. It contains all the high-level logic and exposes an interface for system and applications to use."""

    default_rotate = 0

    def init_display(self, **kwargs):
        """Initializes SH1106 controller. """
        self.rotate = kwargs.pop("rotate", self.default_rotate)
        try:
            self.device = sh1106(self.serial, width=self.width, height=self.height, rotate=self.rotate)
            self.device.real = True
        except:
            self.device = device_mock
        self.reattach_callback = self.reinit_display

    def reinit_display(self):
        try:
            self.device = sh1106(self.serial, width=self.width, height=self.height, rotate=self.rotate)
            self.device_mode = self.device.mode
            self.device.real = True
            self.device.show()
        except:
            self.device = device_mock
        else:
            self.display_image(self.current_image)
        #self.device = sh1106(self.serial, width=self.width, height=self.height, rotate=self.rotate)
        """
        # code from https://github.com/rm-hull/luma.oled/blob/main/luma/oled/device/__init__.py at eb6d321a
        settings = {
            (128, 128): dict(multiplex=0xFF, displayoffset=0x02),
            (128, 64): dict(multiplex=0x3F, displayoffset=0x00),
            (128, 32): dict(multiplex=0x20, displayoffset=0x0F)
        }.get((self.width, self.height))

        self.device.command(
            self.device._const.DISPLAYOFF,
            self.device._const.MEMORYMODE,
            self.device._const.SETHIGHCOLUMN,      0xB0, 0xC8,
            self.device._const.SETLOWCOLUMN,       0x10, 0x40,
            self.device._const.SETSEGMENTREMAP,
            self.device._const.NORMALDISPLAY,
            self.device._const.SETMULTIPLEX,       settings['multiplex'],
            self.device._const.DISPLAYALLON_RESUME,
            self.device._const.SETDISPLAYOFFSET,   settings['displayoffset'],
            self.device._const.SETDISPLAYCLOCKDIV, 0xF0,
            self.device._const.SETPRECHARGE,       0x22,
            self.device._const.SETCOMPINS,         0x12,
            self.device._const.SETVCOMDETECT,      0x20,
            self.device._const.CHARGEPUMP,         0x14)
        self.device.contrast(0x7F)
        self.device.clear()
        self.device.show()
        self.display_image(self.current_image)
        """
