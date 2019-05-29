from copy import copy
from time import sleep
from threading import Lock, Event
from functools import wraps

from helpers import setup_logger, remove_left_failsafe, cb_needs_key_state, \
                    KEY_PRESSED, KEY_RELEASED, KEY_HELD
from utils import to_be_foreground, check_value_lock
from base_ui import BaseUIElement
from base_view_ui import BaseViewMixin, BaseView

logger = setup_logger(__name__, "warning")

def check_position_overflow(condition):
    """Returns a decorator which can check for different ways of "self.position" counter overflow """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            #First, different checks depending on the type of check requested
            if condition == ">":
                overflow = self.position > len(self.value) # The biggest difference should be 1 character - for when position has advanced, but no character has been input
                difference = (len(self.value) - self.position) + 1
            elif condition == ">=":
                overflow = self.position >= len(self.value) #Can't be any positive difference, when updating the position pointer should be on an existing character
                difference = len(self.value) - self.position
            #Taking action if overflow happened
            if overflow:
                #TODO: insert proper logging
                #Fixing the overflow by adding space characters
                for _ in range(difference):
                    value.append(" ")
            #Checks done, executing decorated function
            result = func(self, *args, **kwargs)
            return result
        return wrapper
    return decorator


class NumpadCharInput(BaseViewMixin, BaseUIElement):
    """Implements a character input UI element for a numeric keypad, allowing to translate numbers into characters.

    Attributes:

    * ``value``: currently entered number string.
    * ``in_foreground``: A flag which indicates if UI element is currently displayed. If it's not active, inhibits any of element's actions which can interfere with other UI element being displayed.

    """

    default_mapping = {"1":"1!?$&|\\",
               "2":"abc2ABC",
               "3":"def3DEF",
               "4":"ghi4GHI",
               "5":"jkl5JKL",
               "6":"mno6MNO",
               "7":"pqrs7PQRS",
               "8":"tuv8TUV",
               "9":"wxyz9WXYZ",
               "0":" 0+@_:-;=%",
               "*":"*.,'\"^",
               "#":"#/()[]<>",
              }

    held_mapping = {str(i):str(i) for i in range(10)}

    action_keys = {
               "KEY_F1":"deactivate",
               "KEY_F2":"backspace",
               "KEY_ENTER":"accept_value",
               "KEY_LEFT":"deactivate_if_first",
               "KEY_RIGHT":"skip"
              }

    bottom_row_buttons = ["Cancel", "OK", "Erase"]
    spacer_character = ' '

    value = ""
    position = 0
    value_lock = None
    pending_character = None
    pending_counter = 0
    pending_counter_start = 10 #Multiples of 0.1 second interval
    current_letter_num = 0
    __locked_name__ = None

    config_key = "dialog"
    default_char_view = "TextView"

    def __init__(self, i, o, message="Value:", value="", name="NumpadCharInput", mapping=None, config={}):
        """Initialises the NumpadCharInput object.

        Args:

            * ``i``, ``o``: input&output device objects
            * ``message``: message to show at the top of the screen
            * ``name``: name of the UI element, useful for debugging
            * ``mapping``: alternative key-to-characters mapping to use

        """
        self.action_keys = copy(self.action_keys)
        BaseUIElement.__init__(self, i, o, name)
        self.message = message
        self.value = value
        self.position = len(self.value)
        if mapping is not None:
            self.mapping = copy(mapping)
        else:
            self.mapping = copy(self.default_mapping)
        self.value_lock = Lock()
        self.value_accepted = False
        BaseViewMixin.__init__(self, config=config)

    def generate_views_dict(self):
        return {"TextView": TextView}

    def before_foreground(self):
        self.value_accepted = False
        self.in_foreground = True

    def before_activate(self):
        self.o.cursor()

    def after_activate(self):
        self.o.noCursor()
        self.i.remove_streaming()

    def get_return_value(self):
        if self.value_accepted:
            return self.value
        else:
            return None

    def idle_loop(self):
        sleep(0.1)
        self.check_character_state()

    def deactivate_if_first(self):
        """ Deactivates the UI element if it hasn't yet had a character entered """
        if self.position == 0:
            self.deactivate()

    def accept_value(self):
        logger.info("{0}: accepted value".format(self.name))
        self.value_accepted = True
        self.deactivate()

    # Functions processing user input.

    # @cb_needs_key_state can't be applied on top since it will get applied to
    # check_value_lock and set a flag on it (which will result in a confusing bug)
    @check_value_lock
    @cb_needs_key_state
    def process_streaming_keycode(self, key_name, state=None, *args):
        # This function processes all keycodes - both number keycodes and action keycodes
        header = "KEY_"
        key = key_name[len(header):]
        if state == KEY_RELEASED:
            # We don't do anything on "key released" for now
            return
        elif state == KEY_HELD:
            # "Key held" behaviour: pick a character out of the mapping and advancing input
            # That is, if the character is in the mapping at all, action keys are still
            # processed by this loop (for whatever reason, I thought I split them out?)
            if self.pending_character and key in self.mapping:
                self.pending_character = None
                self.pending_counter = self.pending_counter_start
                # Picking a "suitable" character
                if hasattr(self, "held_mapping") and key in self.held_mapping:
                    letter = self.held_mapping[key]
                elif key in list(self.mapping[key]) and not self.mapping[key].startswith(key):
                    # If a keypad character name (0-9*# range in case of ZeroPhone)
                    # is in the mapping, but isn't the beginning of it, change current
                    # character to it
                    letter = key
                else:
                    # Otherwise, use the last character
                    letter = self.mapping[key][-1]
                # Letter picked, adding and advancing
                self.update_letter_in_value(letter)
                self.position += 1
                self.refresh()
            return
        if state not in (None, KEY_PRESSED):
            logger.error("Unknown key state: {}! Can't process".format(key))
            return
        # Further code processes "key pressed" situation
        logger.debug("Received "+key_name)
        if key in self.mapping:
            #It's one of the keys we can process
            #NO INSERT IN MIDDLE/START SUPPORT
            if self.pending_character is None: #Currently no key pending
                #The position should be updated by now
                #Starting with first letter in the mapping for current key
                self.current_letter_num = 0
                letter = self.mapping[key][0]
                self.insert_letter_in_value(letter)
                if len(self.mapping[key]) == 1:
                    #No other characters that could be entered by using "pending character" function
                    #Thus, just moving forward
                    self.position += 1
                    #pending_character is already None so "pending letter" mechanism is disabled
                else:
                    #Other letters possible for the key
                    #So, onto the "countdown before character accepted" mechanism
                    self.pending_character = key
                    #Starting the "time before the character is accepted" countdown
                    self.pending_counter = self.pending_counter_start
                    #Output things on display
            elif self.pending_character != key: #Currently another key pending
                #Advancing position and inserting a new letter
                self.position += 1
                #Starting with first letter in the mapping for current key
                self.current_letter_num = 0
                letter = self.mapping[key][0]
                self.insert_letter_in_value(letter)
                if len(self.mapping[key]) == 1:
                    #No other characters that could be entered
                    #Thus, just setting pending_character to None
                    self.pending_character = None
                    #Need to move forward once again - cursor still points at the previous character
                    self.position += 1
                else:
                    #There are other characters possible for the new letter
                    #So, onto the "countdown before character accepted" mechanism
                    self.pending_character = key
                    #Starting the "time before the character is accepted" countdown
                    self.pending_counter = self.pending_counter_start
                    #Output things on display
            elif self.pending_character == key: #Current pending key is the same as the one pressed
                #Just updating the value and resetting the countdown
                self.current_letter_num += 1
                #Wrapping around in case of overflow
                if self.current_letter_num not in range(len(self.mapping[key])):
                    self.current_letter_num = 0
                letter = self.mapping[key][self.current_letter_num]
                #Replacing the current character
                self.update_letter_in_value(letter)
                #For fast typists, not resetting the counter could be an option in the future
                #That'd mean there'd be only 1 second in total to choose from all letters, so it needs to be tested
                self.pending_counter = self.pending_counter_start
            #Finally, output all changes to display
            self.refresh()

    def backspace(self):
        self.remove_letter_in_value()
        self.refresh()

    #Functions that do processing on the current value

    @check_position_overflow(">")
    def insert_letter_in_value(self, letter):
        if self.position in range(len(self.value)):
            #Inserting character in the middle of the string
            value_before_letter = self.value[:self.position]
            value_after_letter = self.value[self.position:]
            self.value = "".join([value_before_letter, letter, value_after_letter])
        elif self.position == len(self.value): #Right on the last character
            self.value += letter
        else:
            #Inserting afterwards?
            for _ in range(self.position-len(self.value)):
                self.value += self.spacer_character
            self.value += letter

    @check_position_overflow(">=")
    def update_letter_in_value(self, letter):
        #Split the value string to list of characters, replace the letter and assemble the string again
        value_l = list(self.value)
        value_l[self.position] = letter
        self.value = "".join(value_l)

    @check_position_overflow(">")
    def remove_letter_in_value(self):
        if self.position == 0 and not self.value:
            #Nothing to be done
            return None
        elif self.position in [len(self.value)-1] and self.pending_character is not None:
            #Trying to remove the character which is currently pending
            self.pending_character = None
            self.value = self.value[:-1]
        elif self.position in range(len(self.value)):
            #Inserting character in the middle of the string
            value_before_letter = self.value[:self.position-1]
            value_after_letter = self.value[self.position:]
            self.value = "".join(value_before_letter, value_after_letter)
            self.position -= 1
        elif self.position == len(self.value):
            #Just removing the last character
            self.value = self.value[:-1]
            self.position -= 1

    #Functions that work with "pending counter"

    @check_value_lock
    def check_character_state(self):
        if self.pending_character is not None:
            #Character still pending
            self.pending_counter -= 1
            if self.pending_counter == 0:
                self.skip() # advancing to the next character

    def skip(self):
        #Counter reset
        self.pending_character = None
        #Advancing position so that cursor takes the next space
        self.position += 1
        self.refresh()

    #Functions that set up the input listener

    def generate_keymap(self):
        return copy(self.action_keys)

    @to_be_foreground
    def configure_input(self):
        BaseUIElement.configure_input(self)
        self.i.set_streaming(self.process_streaming_keycode)

    #Functions that are responsible for input to display

    def get_displayed_value(self):
        """
        A simple function to get the actually displayed value;
        might be overridden by child elements (like NumpadPasswordInput)
        """
        return self.value

    #Debug-related functions.

    def print_value(self):
        """ A debug method. Useful for hooking up to an input event so that you can see current value. """
        logger.info(self.value)


class NumpadPasswordInput(NumpadCharInput):
    """
    Implements a password input UI element for a numeric keypad, with the same mapping
    as NumpadCharInput, but hiding all characters except the one that's currently being typed.
    """

    def __init__(self, *a, **k):
        NumpadCharInput.__init__(self, *a, **k)
        self.pw_value_displayed = Event()

    def generate_keymap(self):
        km = NumpadCharInput.generate_keymap(self)
        km["KEY_UP"] = self.toggle_pw_display
        return km

    def toggle_pw_display(self):
        if self.pw_value_displayed.isSet():
            self.pw_value_displayed.clear()
        else:
            self.pw_value_displayed.set()

    def get_displayed_value(self):
        if self.value:
            if self.pw_value_displayed.isSet():
                return self.value
            masked_string = "*"*len(self.value)
            if self.pending_character:
                masked_string = masked_string[:-1] + self.value[-1] # unmask the last character
            return masked_string
        else:
            return ""


class NumpadNumberInput(NumpadCharInput):
    """Implements a number input UI element for a numeric keypad, allowing to translate number keys into numbers."""

    #Quite straightforward mapping for now
    default_mapping = {"1":"1",
               "2":"2",
               "3":"3",
               "4":"4",
               "5":"5",
               "6":"6",
               "7":"7",
               "8":"8",
               "9":"9",
               "0":"0",
               "*":"*",
               "#":"#"}


class NumpadHexInput(NumpadCharInput):
    """Implements a hexadecimal number input UI element for a numeric keypad, allowing to translate number keys into hexadecimal numbers."""

    spacer_character = 'x'
    default_mapping = {"1":"1",
               "2" :"2",
               "3" :"3",
               "4" :"4",
               "5" :"5",
               "6" :"6",
               "7" :"7",
               "8" :"8",
               "9" :"9",
               "0" :"0",
               "F3":"A",
               "F4":"B",
               "*" :"C ",
               "#" :"Dx",
               "F5":"E",
               "F6":"F"}

class NumpadKeyboardInput(NumpadCharInput):
    """Implements a normal keyboard input"""

    default_mapping = {}
    keys = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"

    action_keys = {
       "KEY_ENTER":"accept_value",
       "KEY_F1":"deactivate",
       "KEY_LEFT":"deactivate_if_first",
       "KEY_RIGHT":"skip",
       "KEY_F2":"backspace",
       "KEY_BACKSPACE": "backspace"
    }

    for c in keys:
        default_mapping[c] = c.lower()
        default_mapping[c] += c

    default_mapping["SPACE"] = " "

# Views

class TextView(BaseView):
    def get_displayed_data(self):
        """Experimental: not meant for 2x16 displays

        Formats the value and the message to show it on the screen, then returns a list that can be directly used by o.display_data"""
        displayed_data = [self.el.message]
        screen_rows = self.o.rows
        screen_cols = self.o.cols
        static_line_count = 2 #One for message, another for context key labels
        value = self.el.get_displayed_value()
        lines_taken_by_value = (len(value) / (screen_cols)) + 1
        for line_i in range(lines_taken_by_value):
            displayed_data.append(value[(line_i*screen_cols):][:screen_cols])
        empty_line_count = screen_rows - (static_line_count + lines_taken_by_value)
        for _ in range(empty_line_count):
            displayed_data.append("") #Just empty line
        third_line_length = screen_cols/3
        button_labels = [button.center(third_line_length) for button in self.el.bottom_row_buttons]
        last_line = "".join(button_labels)
        displayed_data.append(last_line)
        return displayed_data

    def get_cursor_pos(self):
        cursor_y, cursor_x = divmod(self.el.position, self.o.cols)
        cursor_y += 1
        return (cursor_y, cursor_x)

    def refresh(self):
        """Function that is called each time data has to be output on display"""
        return self.character_refresh()
