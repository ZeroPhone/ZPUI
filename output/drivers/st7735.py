from luma.lcd.device import st7735

from output.output import OutputDevice
from output.drivers.backlight import BacklightManager
from output.drivers.luma_driver import LumaScreen

class Screen(LumaScreen, OutputDevice):

  default_height = 128
  default_width = 128
  default_rotate = 0
  default_h_offset = 0
  default_v_offset = 0

  def init_display(self, **kwargs):
      self.rotate = kwargs.pop("rotate", self.default_rotate)
      self.h_offset = kwargs.pop("h_offset", self.default_h_offset)
      self.v_offset = kwargs.pop("v_offset", self.default_v_offset)
      width = self.height if self.rotate%2==1 else self.width
      height = self.width if self.rotate%2==1 else self.height
      gpio = kwargs.pop("gpio", None)
      self.device = st7735(self.serial, width=width, height=height, bgr=True, rotate=self.rotate, h_offset=self.h_offset, v_offset=self.v_offset, gpio=gpio)

  def enable_backlight(self, *args, **kwargs):
      BacklightManager.enable_backlight(self, *args, **kwargs)

  def disable_backlight(self, *args, **kwargs):
      BacklightManager.disable_backlight(self, *args, **kwargs)
