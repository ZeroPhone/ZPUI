from threading import Lock
from time import time

from ui.menu import Menu
from ui.utils import clamp, check_value_lock, to_be_foreground


class NumberedMenu(Menu):
    """
    This Menu allows the user to jump to entries using the numpad. If the menu is 10 entries or less
    the navigation is instant. Otherwise, it lets the user type multiple digits to navigate to entries beyond 10th.

    The `input_delay` parameter controls how long, and if, the menu waits before considering an input as definitive.
    If `input_delay` is 0, then only the 10 first entries can be navigated to using the keypad.

    The `prepend_numbers` parameters controls whether the entries should be prefixed by their number.
    (default: `True`)
    """

    def __init__(self, *args, **kwargs):
        self.prepend_numbers = kwargs.pop('prepend_numbers', True)
        self.input_delay = kwargs.pop('input_delay', 1)
        Menu.__init__(self, *args, **kwargs)
        self.__locked_name__ = None
        self.value_lock = Lock()
        self.numeric_keymap = {"KEY_{}".format(i): i for i in range(10)}
        self.last_input_time = 0
        self.current_input = None

    @property
    def entry_count(self):
        return len(self.contents)

    def before_activate(self):
        Menu.before_activate(self)
        self.last_input_time = -self.input_delay

    def idle_loop(self):
        Menu.idle_loop(self)
        self.check_character_state()

    def configure_input(self):
        Menu.configure_input(self)
        self.i.set_streaming(self.on_key_pressed)

    def deactivate(self):
        Menu.deactivate(self)
        self.i.remove_streaming()

    @to_be_foreground
    def on_key_pressed(self, key):
        if key == "KEY_RIGHT" and self.is_multi_digit():
            self.confirm_current_input()

        if key not in self.numeric_keymap:
            return
        if self.is_multi_digit():
            self.process_multi_digit_input(key)
        else:
            self.process_single_digit_input(key)
        self.view.refresh()

    def process_single_digit_input(self, key):
        self.move_to_entry(self.numeric_keymap[key])

    def process_multi_digit_input(self, key):
        self.last_input_time = time()
        if not self.current_input:
            self.current_input = str(self.numeric_keymap[key])
        else:
            self.current_input += str(self.numeric_keymap[key])

    def move_to_entry(self, index):
        if self.pointer == index:
            # Moving to the same item that's already selected
            # let's interpret this as KEY_ENTER
            self.current_input = None
            self.select_entry()
            return
        self.pointer = clamp(index, 0, len(self.contents) - 1)
        self.current_input = None
        self.view.refresh()

    def get_displayed_contents(self):
        """
        Overriding this function lets us have entry numbers while
        not modifying the actual ``contents`` of the menu
        """
        if self.prepend_numbers:
            return self.get_contents_with_numbers()
        else:
            return self.contents

    def get_contents_with_numbers(self):
        # prepend numbers to each entry name
        if self.is_multi_digit():
            return [["{} {}".format(i, entry[0]), entry[1]]
                    for i, entry in enumerate(self.contents)]
        else:
            numbered_contents = copy(numbered_contents)
            for i, entry in enumerate(numbered_contents[:10]):
                entry[0] = "{} {}".format(i, entry[0])
            return numbered_contents

    @check_value_lock
    def check_character_state(self):
        if self.is_current_input_finished():
            self.move_to_entry(int(self.current_input))

    def is_multi_digit(self):
        return self.input_delay > 0

    def is_current_input_finished(self):
        # nothing in the buffer
        if not self.current_input:
            return False

        # no need to let the user input '100' if we have 20 entries
        if len(str(self.current_input)) == len(str(self.entry_count)):
            return True

        # user typed 2 and we have 19 entries, going to the most likely option
        if int(self.current_input) * 10 > self.entry_count:
            return True

        # user typed 17 and we have 12 entries
        if int(self.current_input) >= self.entry_count:
            return True

        now = time()
        elapsed = now - self.last_input_time
        if self.is_multi_digit() and elapsed >= self.input_delay:  # delay wait is over
            return True
        return False

    def confirm_current_input(self):
        if self.current_input is None:
            return
        self.move_to_entry(int(self.current_input))
