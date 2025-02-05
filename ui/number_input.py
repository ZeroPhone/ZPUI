from time import sleep
from copy import copy

from ui.utils import to_be_foreground
from ui.base_ui import BaseUIElement
from helpers import setup_logger
logger = setup_logger(__name__, "warning")

class IntegerAdjustInput(BaseUIElement):
    """Implements a simple number input dialog which allows you to increment/decrement a number using  which can be used to navigate through your application, output a list of values or select actions to perform. Is one of the most used elements, used both in system core and in most of the applications.

    Attributes:

    * ``number``: The number being changed.
    * ``initial_number``: The number sent to the constructor. Used by reset() method.
    * ``selected_number``: A flag variable to be returned by activate().
    * ``in_foreground`` : a flag which indicates if UI element is currently displayed. If it's not active, inhibits any of element's actions which can interfere with other UI element being displayed.

    """
    in_foreground = False
    name = ""
    message = ""
    initial_number = 0
    number = 0
    selected_number = None

    def __init__(self, number, i, o, message="Pick a number:", interval=1, name="IntegerAdjustInput", mode="normal", max=None, min=None):
        """Initialises the IntegerAdjustInput object.

        Args:

            * ``number``: number to be operated on
            * ``i``, ``o``: input&output device objects

        Kwargs:

            * ``message``: Message to be shown on the first line of the screen while UI element is active.
            * ``interval``: Value by which the number is incremented and decremented.
            * ``name``: UI element name which can be used internally and for debugging.
            * ``mode``: Number display mode, either "normal" (default) or "hex" ("float" will be supported eventually)
            * ``min``: minimum value, will not go lower than that.
            * ``max``: maximum value, will not go higher than that.

        """
        BaseUIElement.__init__(self, i, o, name)
        if type(number) != int:
            raise ValueError("IntegerAdjustInput operates on integers!")
        self.number = number
        self.min = min
        self.max = max
        self.clamp()
        self.initial_number = self.number
        self.message = message
        self.mode = mode
        self.interval = interval

    def get_return_value(self):
        return self.selected_number

    def idle_loop(self):
        sleep(0.1)

    def print_number(self):
        """ A debug method. Useful for hooking up to an input event so that you can see current number value. """
        logger.info(self.number)

    def decrement(self, multiplier=1):
        """Decrements the number by selected ``interval``"""
        self.number -= self.interval*multiplier
        self.clamp()
        self.refresh()

    def increment(self, multiplier=1):
        """Increments the number by selected ``interval``"""
        self.number += self.interval*multiplier
        self.clamp()
        self.refresh()

    @to_be_foreground
    def reset(self):
        """Resets the number, setting it to the number passed to the constructor."""
        logger.debug("Number reset")
        self.number = self.initial_number
        self.clamp()
        self.refresh()

    @to_be_foreground
    def select_number(self):
        """Selects the currently active number value, making activate() return it."""
        logger.debug("Number accepted")
        self.selected_number = self.number
        self.deactivate()

    @to_be_foreground
    def exit(self):
        """Exits discarding all the changes to the number."""
        logger.debug("{} exited without changes".format(self.name))
        self.deactivate()

    def generate_keymap(self):
        return {
        "KEY_RIGHT":'reset',
        "KEY_UP":'increment',
        "KEY_DOWN":'decrement',
        "KEY_F3":lambda: self.increment(multiplier=10),
        "KEY_F4":lambda: self.decrement(multiplier=10),
        "KEY_ENTER":'select_number',
        "KEY_LEFT":'exit'
        }

    def clamp(self):
        """
        Clamps the number if either ``min`` or ``max`` are set.
        """
        if self.min is not None and self.number < self.min:
            self.number = self.min
        if self.max is not None and self.number > self.max:
            self.number = self.max

    def get_displayed_data(self):
        if self.mode == "hex":
            number_str = hex(self.number)
        else:
            number_str = str(self.number)
        number_str = number_str.rjust(self.o.cols)
        return [self.message, number_str]

    @to_be_foreground
    def refresh(self):
        logger.debug("{0}: refreshed data on display".format(self.name))
        self.o.display_data(*self.get_displayed_data())
