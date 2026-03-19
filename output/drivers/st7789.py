from luma.lcd.device import st7789

from output.output import OutputDevice
from output.drivers.backlight import BacklightManager
from output.drivers.luma_driver import LumaScreen

function_mock = lambda *a, **k: True
device_mock = type("ST7789", (), {"mode":'1', "size":(240, 240), "display": function_mock, "hide": function_mock, "show": function_mock, "real":False})

class Screen(LumaScreen, OutputDevice):

    default_height = 240
    default_width = 240
    default_rotate = 0

    def init_display(self, **kwargs):
        self.rotate = kwargs.pop("rotate", self.default_rotate)
        width = self.height if self.rotate%2==1 else self.width
        height = self.width if self.rotate%2==1 else self.height
        device_mock.mode = (width, height)
        gpio = kwargs.pop("gpio", None)
        try:
            self.device = st7789(self.serial, width=self.width, height=self.height, rotate=self.rotate, gpio=gpio)
            self.device.real = True
        except:
            self.device = device_mock
        self.reattach_callback = self.reinit_display

    def reinit_display(self):
        try:
            self.device = st7789(self.serial, width=self.width, height=self.height, rotate=self.rotate, gpio=gpio)
            self.device_mode = self.device.mode
            self.device.real = True
            self.device.show()
        except:
            self.device = device_mock
        else:
            self.display_image(self.current_image)

    def enable_backlight(self, *args, **kwargs):
        BacklightManager.enable_backlight(self, *args, **kwargs)

    def disable_backlight(self, *args, **kwargs):
        BacklightManager.disable_backlight(self, *args, **kwargs)
