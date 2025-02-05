#!/usr/bin/env python2

"""
This module is as complicated as it is because it was necessary to work
around the fact that pygame (which this emulator is based on) doesn't
like multi-threaded environments, in particular, it doesn't like when
input and output are done from two different threads. For this reason,
the pygame IO is done in a different process, and we're using
multiprocessing.Pipe to communicate with this process. Part of the
complexity is also the fact that nobody (including me) bothered to
implement a two-way communication, so there's yet no way to get callable
return values and, as a result, attribute values. If you're reading this,
consider helping us with it - this way, we could be free from all the
hardcoded values in EmulatorProxy =)
"""

from multiprocessing import Process, Pipe
from threading import Lock
from time import sleep

import luma.emulator.device
import pygame
from luma.core.render import canvas

from helpers import setup_logger, KEY_PRESSED, KEY_RELEASED, KEY_HELD
from output.output import GraphicalOutputDevice, CharacterOutputDevice

logger = setup_logger(__name__, "warning")

# A singleton - since the same object needs to be called
# both in the pygame output and pygame input drivers.
__EMULATOR_PROXY = None

def get_emulator():
    global __EMULATOR_PROXY
    if __EMULATOR_PROXY is None:
        __EMULATOR_PROXY = EmulatorProxy()
    return __EMULATOR_PROXY


class EmulatorProxy(object):

    device_mode = "1"
    char_width = 6
    char_height = 8
    type = ["char", "b&w"]

    def __init__(self, mode="1", width=128, height=64):
        self.width = width
        self.height = height
        self.mode = mode
        self.device_mode = mode
        self.device = type("MockDevice", (), {"mode":self.mode, "size":(self.width, self.height)})
        self.parent_conn, self.child_conn = Pipe()
        self.__base_classes__ = (GraphicalOutputDevice, CharacterOutputDevice)
        self.current_image = None
        self.start_process()

    def start_process(self):
        self.proc = Process(target=Emulator, args=(self.child_conn,), kwargs={"mode":self.mode, "width":self.width, "height":self.height})
        self.proc.start()

    def poll_input(self, timeout=1):
        if self.parent_conn.poll(timeout) is True:
            return self.parent_conn.recv()
        return None

    def quit(self):
        DummyCallableRPCObject(self.parent_conn, 'quit')()
        self.proc.join()

    def __getattr__(self, name):
        # Raise an exception if the attribute being called
        # doesn't actually exist on the Emulator object
        getattr(Emulator, name)
        # Otherwise, return an object that imitates the requested
        # attribute of the Emulator - for now, only callables
        # are supported, and you can't get the result of a
        # callable.
        return DummyCallableRPCObject(self.parent_conn, name)


class DummyCallableRPCObject(object):
    """
    This is an object that allows us to call functions of the Emulator
    that's running as another process. In the future, it might also support
    getting attributes and passing return values (same thing, really),
    which should also allow us to get rid of hard-coded parameters
    in the EmulatorProxy object.
    """
    def __init__(self, parent_conn, name):
        self.parent_conn = parent_conn
        self.__name__ = name

    def __call__(self, *args, **kwargs):
        self.parent_conn.send({
            'func_name': self.__name__,
            'args': args,
            'kwargs': kwargs
        })


class Emulator(object):
    def __init__(self, child_conn, mode="1", width=128, height=64):
        self.child_conn = child_conn

        self.width = width
        self.height = height

        self.char_width = 6
        self.char_height = 8

        self.cols = self.width // self.char_width
        self.rows = self.height // self.char_height

        self.cursor_enabled = False
        self.cursor_pos = [0, 0]
        self._quit = False

        self.key_delay = 1000
        self.key_interval = 1000

        self.emulator_attributes = {
            'display': 'pygame',
            'width': self.width,
            'height': self.height,
        }

        self.busy_flag = Lock()
        self.pressed_keys = []
        self.init_hw()
        self.runner()

    def init_hw(self):
        Device = getattr(luma.emulator.device, self.emulator_attributes['display'])
        self.device = Device(**self.emulator_attributes)
        pygame.key.set_repeat(self.key_delay, self.key_interval)

    def runner(self):
        try:
            self._event_loop()
        except KeyboardInterrupt:
            logger.info('Caught KeyboardInterrupt')
        except:
            logger.exception('Unknown exception during event loop')
            raise
        finally:
            self.child_conn.close()

    def _poll_input(self):
        event = pygame.event.poll()
        if event.type in [pygame.KEYDOWN, pygame.KEYUP]:
            key = event.key
            state = {pygame.KEYDOWN: KEY_PRESSED, \
                     pygame.KEYUP: KEY_RELEASED} \
                               [event.type]
            # Some filtering logic to add KEY_HELD and keep track of pressed keys
            if state == KEY_PRESSED and key in self.pressed_keys:
                state = KEY_HELD
            elif state == KEY_PRESSED:
                self.pressed_keys.append(key)
            elif state == KEY_RELEASED:
                if key in self.pressed_keys:
                    self.pressed_keys.remove(key)
            self.child_conn.send({'key': key, 'state':state})

    def _poll_parent(self):
        if self.child_conn.poll() is True:
            event = self.child_conn.recv()
            func = getattr(self, event['func_name'])
            try:
                func(*event['args'], **event['kwargs'])
            except:
                import traceback; traceback.print_exc()

    def _event_loop(self):
        while self._quit is False:
            self._poll_parent()
            self._poll_input()
            sleep(0.001)

    def setCursor(self, row, col):
        self.cursor_pos = [
            col * self.char_width,
            row * self.char_height,
        ]

    def quit(self):
        self._quit = True

    def noCursor(self):
        self.cursor_enabled = False

    def cursor(self):
        self.cursor_enabled = True

    def display_image(self, image, **kwargs):
        """
        Displays a PIL Image object onto the display
        Also saves it for the case where display needs to be refreshed.
        Accepts **kwargs but ignores them - hack, since other (i.e. backlight-enabled)
        drivers can accept (and sometimes are sent) kwargs.
        """
        with self.busy_flag:
            self.current_image = image
            self._display_image(image)

    def _display_image(self, image):
        self.device.display(image)

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
            d.rectangle(dims, outline="white")
        for line, arg in enumerate(args):
            y = (line * self.char_height - 1) if line != 0 else 0
            d.text((2, y), arg, fill="white")
        return draw.image

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
