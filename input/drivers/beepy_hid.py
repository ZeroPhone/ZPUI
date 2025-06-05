from evdev import InputDevice as HID, list_devices, ecodes
from time import sleep

from zpui_lib.helpers import setup_logger
from input.drivers.hid import InputDevice as HIDDevice

logger = setup_logger(__name__, "warning")

class InputDevice(HIDDevice):
    """ A driver for Beepy HID. Supports the keyboard and the touchpad in arrow key mode."""

    default_name_mapping = {"KEY_KPENTER":"KEY_ENTER", "KEY_PAGEUP":"KEY_F3", "KEY_PAGEDOWN":"KEY_F4", "KEY_ESC":"KEY_LEFT", "KEY_LEFTCTRL":"KEY_PROG2"}

    beepy_mapping = {
        # numpad
        "KEY_FIND":"KEY_1",
        "KEY_CUT":"KEY_2",
        "KEY_HELP":"KEY_3",
        "KEY_WWW":"KEY_4",
        "KEY_MSDOS":"KEY_5",
        "KEY_COFFEE+KEY_SCREENLOCK":"KEY_6",
        "KEY_NEXTSONG":"KEY_7",
        "KEY_PLAYPAUSE":"KEY_8",
        "KEY_PREVIOUSSONG":"KEY_9",
        "KEY_PROPS":"KEY_0",
        # first row (except numpad)
        "KEY_PASTE":"KEY_HASH", # one left of numpad
        "KEY_MENU":"KEY_LEFTPAREN",
        "KEY_CALC":"KEY_RIGHTPAREN",
        "KEY_SETUP":"KEY_UNDERSCORE",
        "KEY_SLEEP":"KEY_MINUS",
        "KEY_WAKEUP":"KEY_PLUS",
        "KEY_FILE":"KEY_AT",
        # second row (except numpad)
        "KEY_PROG2":"KEY_ASTERISK", # one key left of numpad
        "KEY_DIRECTION+KEY_ROTATE_DISPLAY":"KEY_SLASH",
        "KEY_CYCLEWINDOWS":"KEY_COLON",
        "KEY_MAIL":"KEY_SEMICOLON",
        "KEY_BOOKMARKS":"KEY_QUOTE",
        "KEY_COMPUTER":"KEY_DOUBLEQUOTE",
        "KEY_COPY":"KEY_BACKSPACE", # mapping backspace even when alt-modified
        "KEY_XFER":"KEY_ENTER", # mapping enter even when alt-modified
        # third row (except numpad)
        "KEY_STOPCD":"KEY_QUESTION",
        "KEY_RECORD":"KEY_EXCLAMATION",
        "KEY_REWIND":"KEY_COMMA",
        "KEY_PHONE":"KEY_DOT",
        "KEY_REPLY":"KEY_UNMUTE",
        "KEY_0":"KEY_MUTE",
        "KEY_MIN_INTERESTING+KEY_MUTE":"KEY_DOLLAR",
    }
    touchpad_keys = ["KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT"]

    tt_path = "/sys/module/beepy_kbd/parameters/touch_threshold"
    orig_tt = None

    def __init__(self, name="beepy-kbd", tt=64, **kwargs):
        """Initialises the ``InputDevice`` object.

        Kwargs:

            * ``name``: beepy input device name to expect
            * ``tt``: touch threshold that the driver will set. the driver will revert to the previous touch threshold when ZPUI exits.

        """
        self.name = name
        self.tt = tt
        HIDDevice.__init__(self, name=self.name, **kwargs)
        self.store_and_replace_tt()
        self.filter_held_keys = False

    def store_and_replace_tt(self):
        """Stores and replaces beepy kbd driver touch threshold"""
        with open(self.tt_path, 'rb') as f:
           self.orig_tt = f.read().strip()
        tt_bytes = bytes(str(self.tt), "ascii")
        logger.info("replacing the original touch threshold {} with {}".format( repr(self.orig_tt), repr(tt_bytes) ))
        with open(self.tt_path, 'wb') as f:
           f.write(tt_bytes)

    def set_available_keys(self):
        if hasattr(self, 'device'):
            keys = [ecodes.keys[x] for x in self.device.capabilities()[ecodes.EV_KEY] \
                             if isinstance(ecodes.keys[x], basestring) ]
            keys.append("KEY_3") # funni missing beepis key sob
            self.available_keys = keys
        else:
            self.available_keys = None

    def process_event(self, event):
        if event is not None and event.type == ecodes.EV_KEY:
            key = ecodes.keys[event.code]
            value = event.value
            if self.enabled:
                try:
                    #if key in self.touchpad_keys:
                    #    pass # funni algorithm goes here
                    #else: # keyboard key?
                    if isinstance(key, list):
                        key = "+".join(key)
                    beepy_key = self.beepy_mapping.get(key, key)
                    mapped_key = self.name_mapping.get(beepy_key, beepy_key)
                    logger.debug("Key substitution: k {} b {} m {}".format(key, beepy_key, mapped_key))
                    self.map_and_send_key(mapped_key, state = value)
                except:
                    logger.exception("{}: failed to map and send a key {}".format(self.name, key))

    def atexit(self):
        try:
            InputSkeleton.atexit(self)
        except:
            pass
        try:
            if self.orig_tt:
                with open(self.tt_path, 'wb') as f:
                    f.write(self.orig_tt)
        except:
            pass

if __name__ == "__main__":
    pass
    #print("Available device names:")
    #print([dev.name for dev in get_input_devices()])
    #id = InputDevice(name = get_input_devices()[0].name, threaded=False)
    #id.runner()
