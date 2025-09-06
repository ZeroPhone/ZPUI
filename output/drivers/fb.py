#!/usr/bin/python

# luma.core library used: https://github.com/rm-hull/luma.core

import traceback
from mock import Mock
from threading import Lock

from luma.core.render import canvas
from PIL import ImageChops, Image

import atexit

from zpui_lib.helpers import setup_logger
logger = setup_logger(__name__, "info")

try:
    from ..output import GraphicalOutputDevice, CharacterOutputDevice
except ModuleNotFoundError:
    from output import GraphicalOutputDevice, CharacterOutputDevice

from output.drivers.framebuffer_lib import Framebuffer

function_mock = lambda *a, **k: True


class Screen(GraphicalOutputDevice, CharacterOutputDevice):
    """An object that provides high-level functions for interaction with display. It contains all the high-level logic and exposes an interface for system and applications to use."""

    current_image = None

    default_font = None

    __base_classes__ = (GraphicalOutputDevice, CharacterOutputDevice)

    type = ["char", "b&w"]
    cursor_enabled = False
    cursor_pos = (0, 0) #x, y
    device_mode = None
    char_width = 6
    char_height = 8

    real = True
    suspended = False
    width = None
    height = None

    direct_write = False
    paste_coords = (0, 0)

    def __init__(self, fb_num=1, width=None, height=None, color=True, default_color="white", mul_x=1, mul_y=1, direct_write=False, out_mode="RGBA", disable_cursor=True, **kwargs):
        self.fb_num = fb_num
        self.fb_path = '/dev/fb'+str(self.fb_num)
        if not self.direct_write:
            # and now we create a framebuffer
            self.fb = Framebuffer(self.fb_num)
            self.width, self.height = self.fb.size
            logger.info("Framebuffer device initialized, size: {}, bpp: {}, stride: {}".format(self.fb.size, self.fb.bits_per_pixel, self.fb.stride))
        else:
            # some code taken from here: https://stackoverflow.com/questions/54778105/python-pygame-fails-to-output-to-dev-fb1-on-a-raspberry-pi-tft-screen
            import pygame
            pygame.init()
            self.lcd = pygame.Surface(self.width, self.height)
            self.width, self.height = width, height
        # 'color' argument handling; american-nonamerican spelling
        self.color = color
        if self.color:
            self.device_mode = 'RGB'
            self.type.append("color")
        else:
            self.device_mode = '1'
        self.default_color = default_color
        self.disable_cursor = disable_cursor
        if self.disable_cursor:
            with open('/sys/class/graphics/fbcon/cursor_blink', 'wb') as f:
                f.write(b'0')
            atexit.register(self.atexit)
        self.multiply_x = mul_x
        self.multiply_y = mul_y
        self.out_mode = out_mode
        self.direct_write = direct_write
        self.busy_flag = Lock()
        self.cols = self.width // self.char_width
        self.rows = self.height // self.char_height
        # I forgor what this is for
        self.device = type("FBDevice", (), {"mode":self.device_mode, "size":(self.width, self.height), "display": function_mock, "hide": function_mock, "show": function_mock, "real":False})
        #getattr(self.device, "mode", self.device_mode)
        #BacklightManager.init_backlight(self, **kwargs)

    def suspend(self):
        logger.info("Suspended display {}".format(self))
        self.suspended = True

    def unsuspend(self):
        logger.info("Unsuspended display {}; refreshing image".format(self))
        self.suspended = False
        if self.current_image:
            self._display_image(self.current_image)

    def atexit(self):
        try:
            with open('/sys/class/graphics/fbcon/cursor_blink', 'wb') as f:
                f.write(b'1')
        except:
            logger.exception("Failed to make the cursor blinky again!")

    def get_fbnum_from_path(self, fb_path):
        # function is unused for now
        # `/dev/fbNNN` - how many digits in the end of the name?
        i = -1 # starting with "one digit" and trying to increment further
        while self.fb_path[i-1].isdigit():
            i -= 1
        return int(self.fb_path[i]) # in most cases, i == -1, which returns the last character (`0` for /dev/fb0 or `1` for /dev/fb1)

    def display_image(self, image, backlight_only_on_new=None):
        """
        Displays a PIL Image object onto the display.
        Also saves it for the case where display needs to be refreshed
        """
        if self.suspended: return
        with self.busy_flag:
            self.current_image = image
            self._display_image(image)

    def _display_image(self, image):
        try:
            if not self.direct_write:
                if self.out_mode: # buffer mode overridden
                    buffer = Image.new(mode=self.out_mode, size=self.fb.size)
                else: # using the same mode that ZPUI uses for displaying to this screen
                    buffer = Image.new(mode=self.device_mode, size=self.fb.size)
                if self.multiply_x > 1 or self.multiply_y > 1:
                    image = image.resize((self.width*self.multiply_x, self.height*self.multiply_y), Image.Resampling.NEAREST)
                buffer.paste(image, box=self.paste_coords)
                self.fb.show(buffer)
            else:
                # INCOMPLETE
                # PIL.Image needs to be pasted onto the Pygame surface
                # I found a snippet for it but it's untested
                # source here: https://stackoverflow.com/questions/25202092/pil-and-pygame-image
                with open(self.fb_path, "wb") as f:
                    self.lcd = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
                    # size mismatch expected to happen here
                    f.write(self.lcd.convert(16,0).get_buffer())
        except:
            logger.exception("Couldn't write to the display, fb {}".format(self.fb_num))
            traceback.print_exception()

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

    #@activate_backlight_wrapper
    def display_data(self, *args):
        """Displays data on display. This function does the actual work of printing things to display.

        ``*args`` is a list of strings, where each string corresponds to a row of the display, starting with 0."""
        if self.suspended: return
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



"""
import pygame, time, evdev, select, math

# Now we've got a function that can get the bytes from a pygame surface to the TFT framebuffer,
# we can use the usual pygame primitives to draw on our surface before calling the refresh function.

# Here we just blink the screen background in a few colors with the "Hello World!" text

center_coords = (surfaceSize[0]//2 - 75), (surfaceSize[1]//2 - 10)

pygame.font.init()
defaultFont = pygame.font.SysFont(None,30)

lcd.fill((255,0,0))
lcd.blit(defaultFont.render("Hello World!", False, (0, 0, 0)), center_coords)
refresh()

lcd.fill((0, 255, 0))
lcd.blit(defaultFont.render("Hello World!", False, (0, 0, 0)), center_coords)
refresh()

lcd.fill((0,0,255))
lcd.blit(defaultFont.render("Hello World!", False, (0, 0, 0)), center_coords)
refresh()

lcd.fill((128, 128, 128))
lcd.blit(defaultFont.render("Hello World!", False, (0, 0, 0)), center_coords)
refresh()

#                pygame.draw.circle(lcd, (255, 0, 0), p , 2, 2)
"""
