from evdev import InputDevice as HID, list_devices, ecodes
from time import sleep

from zpui_lib.helpers import setup_logger
from input.drivers.hid import InputDevice as HIDDevice

logger = setup_logger(__name__, "warning")

class InputDevice(HIDDevice):
    """ A driver for Beepy HID. Supports the keyboard and the touchpad in arrow key mode."""

    default_name_mapping = {"KEY_KPENTER":"KEY_ENTER", "KEY_PAGEUP":"KEY_F3", "KEY_PAGEDOWN":"KEY_F4", "KEY_ESC":"KEY_LEFT", "KEY_LEFTCTRL":"KEY_PROG2"}
    touchpad_keys = ["KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT"]

    tt_path = "/sys/module/beepy_kbd/parameters/touch_threshold"
    orig_tt = None

    def __init__(self, name="beepy-kbd", tt=64, **kwargs):
        """Initialises the ``InputDevice`` object.

        Kwargs:

            * ``path``: path to the input device. If not specified, you need to specify ``name``.
            * ``name``: input device name

        """
        self.name = name
        self.tt = tt
        HIDDevice.__init__(self, name=self.name, **kwargs)
        self.store_and_replace_tt()

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
            self.available_keys = keys
        else:
            self.available_keys = None

    def process_event(self, event):
        if event is not None and event.type == ecodes.EV_KEY:
            key = ecodes.keys[event.code]
            value = event.value
            if self.enabled:
                #if key in self.touchpad_keys:
                #    pass # funni algorithm goes here
                #else: # keyboard key?
                key = self.name_mapping.get(key, key)
                self.map_and_send_key(key, state = value)

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
