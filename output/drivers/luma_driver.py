#!/usr/bin/python

#luma.oled library used: https://github.com/rm-hull/luma.oled

from mock import Mock
from threading import Lock

try:
    from luma.core.interface.serial import spi, i2c
except ImportError:
    #Compatilibity with older luma.oled version
    from luma.core.serial import spi, i2c
from luma.core.render import canvas
from luma.core.error import DeviceNotFoundError as DNFError
from PIL import ImageChops

from zpui_lib.helpers import setup_logger
logger = setup_logger(__name__, "warning")

from output.drivers.backlight import *
try:
    from ..output import GraphicalOutputDevice, CharacterOutputDevice
except ModuleNotFoundError:
    from output import GraphicalOutputDevice, CharacterOutputDevice


class LumaScreen(GraphicalOutputDevice, CharacterOutputDevice, BacklightManager):
    """An object that provides high-level functions for interaction with display. It contains all the high-level logic and exposes an interface for system and applications to use."""

    #buffer = " "
    #redraw_coefficient = 0.5
    current_image = None

    default_font = None

    __base_classes__ = (GraphicalOutputDevice, CharacterOutputDevice)

    type = ["char", "b&w"]
    cursor_enabled = False
    cursor_pos = (0, 0) #x, y
    device_mode = None

    hw = None
    port = None
    address = None
    gpio_dc = None
    gpio_rst = None
    width = None
    height = None

    default_i2c_port = 1
    default_spi_port = 0
    default_spi_address = 0
    default_i2c_address = 0x3c
    default_gpio_dc = 6
    default_gpio_rst = 5

    default_width = 128
    default_height = 64
    default_color = "white"

    def __init__(self, hw="spi", port=None, address=None, dc=None, rst=None, \
                      width=None, height=None, default_color="white", **kwargs):
        self.hw = hw
        assert hw in ("spi", "i2c", "dummy"), "Wrong hardware suggested: '{}'!".format(hw)
        # legacy parameters
        if "gpio_dc" in kwargs:
            dc = kwargs.pop("gpio_dc")
        if "gpio_rst" in kwargs:
            dc = kwargs.pop("gpio_rst")
        if self.hw == "spi":
            self.port = port if port != None else self.default_spi_port
            self.address = address if address != None else self.default_spi_address
            self.gpio_dc = dc if dc != None else self.default_gpio_dc
            self.gpio_rst = rst if rst != None else self.default_gpio_rst
            try:
                self.serial = spi(port=self.port, device=self.address, gpio_DC=self.gpio_dc, gpio_RST=self.gpio_rst)
            except TypeError:
                #Compatibility with older luma.oled versions
                self.serial = spi(port=self.port, device=self.address, bcm_DC=self.gpio_dc, bcm_RST=self.gpio_rst)
        elif hw == "i2c":
            self.port = port if port else self.default_i2c_port
            if isinstance(address, basestring): address = int(address, 16)
            self.address = address if address else self.default_i2c_address
            kw = {}
            if rst is not None:
                kw["gpio_RST"] = rst
            self.serial = i2c(port=self.port, address=self.address, **kw)
        elif hw == "dummy":
            self.port = port
            self.address = address
            self.serial = Mock(unsafe=True)
            kwargs["gpio"] = Mock()
        else:
            raise ValueError("Unknown interface type: {}".format(hw))
        self.busy_flag = Lock()
        self.width = width if width else self.default_width
        self.height = height if height else self.default_height
        self.char_width = 6
        self.char_height = 8
        self.cols = self.width // self.char_width
        self.rows = self.height // self.char_height
        self.default_color = default_color
        self.init_display(**kwargs)
        self.device_mode = getattr(self.device, "mode", self.device_mode)
        BacklightManager.init_backlight(self, **kwargs)

    @enable_backlight_wrapper
    def enable_backlight(self):
        if self.device.real: # has the actual device been created yet?
            try:
                self.device.show()
            except (DNFError, OSError):
                logger.warning("couldn't write to the display")

    @disable_backlight_wrapper
    def disable_backlight(self):
        if self.device.real: # has the actual device been created yet?
            try:
                self.device.hide()
            except (DNFError, OSError):
                logger.warning("couldn't write to the display")

    @activate_backlight_wrapper
    def display_image(self, image):
        """Displays a PIL Image object onto the display
        Also saves it for the case where display needs to be refreshed"""
        with self.busy_flag:
            self.current_image = image
            self._display_image(image)

    def trigger_backlight_on_change(self, func_name, *args, **kwargs):
        """
        Hook that allows the backlight driver to determine whether the image has changed.
        """
        if func_name == "display_image":
            image = args[0]
            is_new_image = ImageChops.difference(image, self.current_image).getbbox() is None
            return is_new_image
        elif func_name == "display_data":
            # Redundant, sorry =(
            image = self.display_data_onto_image(*args)
            is_new_image = ImageChops.difference(image, self.current_image).getbbox() is None
            return is_new_image
        else:
            raise ValueError("Unknown function wrapped, wtf?")

    def _display_image(self, image):
        if self.device.real: # has the actual device been created yet?
            try:
                self.device.display(image)
            except (DNFError, OSError):
                logger.warning("couldn't write to the display")

    def display_data_onto_image(self, *args, **kwargs):
        """
        This method takes lines of text and draws them onto an image,
        helping emulate a character display API.
        """
        cursor_position = kwargs.pop("cursor_position", None)
        if not cursor_position:
            cursor_position = self.cursor_pos if self.cursor_enabled else None
        args = args[:self.rows]
        draw = canvas(self.device)
        d = draw.__enter__()
        if cursor_position:
            dims = (self.cursor_pos[0] - 1 + 2, self.cursor_pos[1] - 1, self.cursor_pos[0] + self.char_width + 2,
                    self.cursor_pos[1] + self.char_height + 1)
            d.rectangle(dims, outline=self.default_color)
        for line, arg in enumerate(args):
            y = (line * self.char_height - 1) if line != 0 else 0
            d.text((2, y), arg, font=self.default_font, fill=self.default_color)
        return draw.image

    @activate_backlight_wrapper
    def display_data(self, *args):
        """Displays data on display. This function does the actual work of printing things to display.

        ``*args`` is a list of strings, where each string corresponds to a row of the display, starting with 0."""
        image = self.display_data_onto_image(*args)
        with self.busy_flag:
            self.current_image = image
            self._display_image(image)

    def home(self):
        """Returns cursor to home position. If the display is being scrolled, reverts scrolled data to initial position.."""
        self.setCursor(0, 0)

    def clear(self):
        """Clears the display."""
        draw = canvas(self.device)
        self.display_image(draw.image)
        del draw

    def setCursor(self, row, col):
        """ Set current input cursor to ``row`` and ``column`` specified """
        self.cursor_pos = (col * self.char_width, row * self.char_height)

    def createChar(self, char_num, char_contents):
        """Stores a character in the LCD memory so that it can be used later.
        char_num has to be between 0 and 7 (including)
        char_contents is a list of 8 bytes (only 5 LSBs are used)"""
        pass

    def noDisplay(self):
        """ Turn the display off (quickly) """
        pass

    def display(self):
        """ Turn the display on (quickly) """
        pass

    def noCursor(self):
        """ Turns the underline cursor off """
        self.cursor_enabled = False

    def cursor(self):
        """ Turns the underline cursor on """
        self.cursor_enabled = True

    def noBlink(self):
        """ Turn the blinking cursor off """
        pass

    def blink(self):
        """ Turn the blinking cursor on """
        pass

    def scrollDisplayLeft(self):
        """ These commands scroll the display without changing the RAM """
        pass

    def scrollDisplayRight(self):
        """ These commands scroll the display without changing the RAM """
        pass

    def leftToRight(self):
        """ This is for text that flows Left to Right """
        pass

    def rightToLeft(self):
        """ This is for text that flows Right to Left """
        pass

    def autoscroll(self):
        """ This will 'right justify' text from the cursor """
        pass

    def noAutoscroll(self):
        """ This will 'left justify' text from the cursor """
        pass
