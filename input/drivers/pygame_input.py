from time import sleep
import string

import pygame

import emulator
from helpers import setup_logger
from input.drivers.skeleton import InputSkeleton

logger = setup_logger(__name__, "warning")

numbers = list(range(10))
f_numbers = list(range(1, 13))

USED_KEYS = [str(i) for i in numbers] + \
            ["KP"+str(i) for i in numbers] + \
            ["F"+str(i) for i in f_numbers] + \
            [char for char in string.ascii_lowercase] + \
            ['UP', 'DOWN', 'LEFT', 'RIGHT', 'RETURN', 'PAGEUP', 'PAGEDOWN',
             'ASTERISK', 'HASH', 'PLUS', 'MINUS', 'EQUALS', 'BACKSPACE',
             'KP_MULTIPLY', 'KP_DIVIDE', 'KP_PLUS', 'KP_MINUS', 'SPACE',
             'HOME', 'END']

KEY_MAP = dict([
    (getattr(pygame, 'K_' + key_name), key_name)
    for key_name in USED_KEYS
])


class InputDevice(InputSkeleton):
    """ A driver for pygame-based keyboard key detection."""

    default_name_mapping = { \
                    'KEY_RETURN':'KEY_ENTER',
                    'KEY_KP_ENTER':'KEY_ENTER',
                    'KEY_KP_MULTIPLY':'KEY_*',
                    'KEY_KP_DIVIDE':'KEY_#',
                    'KEY_MINUS':'KEY_HANGUP',
                    'KEY_KP_MINUS':'KEY_HANGUP',
                    'KEY_EQUALS':'KEY_ANSWER',
                    'KEY_KP_PLUS':'KEY_ANSWER',
                    'KEY_PAGEUP':'KEY_F3',
                    'KEY_PAGEDOWN':'KEY_F4',
                    'KEY_F10':'KEY_PROG1',
                    'KEY_F11':'KEY_PROG2',
                    'KEY_F12':'KEY_CAMERA',
                   }

    def __init__(self, **kwargs):
        InputSkeleton.__init__(self, mapping=[], **kwargs)

    def init_hw(self):
        self.emulator = emulator.get_emulator()
        return True

    def set_available_keys(self):
        # Add a KEY_ in front of every value
        temp = ["KEY_{}".format(c.upper()) for c in KEY_MAP.values()]
        self.available_keys = temp

    def runner(self):
        """
        Blocking event loop which just calls supplied callbacks in the keymap.
        """
        #TODO: debug and fix race condition
        while not hasattr(self, "emulator"):
            logger.debug("Input emulator not yet ready, waiting (a bug, TOFIX)")
            sleep(0.1)

        while not self.stop_flag:
            event = self.emulator.poll_input()
            if event is None:
                continue

            key = event['key']
            state = event['state']
            if key not in KEY_MAP:
                logger.debug('Ignoring key %s' % key)
                continue

            key_name = 'KEY_' + KEY_MAP[key]

            kp_m = "KEY_KP" # KP marker to catch KEY_KPx number keys
            if key_name.startswith(kp_m) and key_name[len(kp_m):].isdigit():
                key_name = 'KEY_' + key_name[len(kp_m):]
                logger.debug('Mapped key {} to {}'.format(key, key_name))

            self.map_and_send_key(key_name.upper(), state=state)

        self.emulator.quit()

    def atexit(self):
        InputSkeleton.atexit(self)
