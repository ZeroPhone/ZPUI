from evdev import InputDevice as HID, list_devices, ecodes
from time import sleep

from helpers import setup_logger
from input.drivers.skeleton import InputSkeleton

logger = setup_logger(__name__, "warning")

def get_input_devices():
    """Returns list of all the available InputDevices"""
    devices = []
    for fn in list_devices():
        try:
            devices.append(HID(fn))
        except:
            pass
    return devices

def get_path_by_name(name):
    """Gets HID device path by name, returns None if not found."""
    path = None
    for dev in get_input_devices():
        if dev.name == name:
            path = dev.fn
    return path

def get_name_by_path(path):
    """Gets HID device path by name, returns None if not found."""
    name = None
    for dev in get_input_devices():
        if dev.fn == path:
            name = dev.name
    return name


class InputDevice(InputSkeleton):
    """ A driver for HID devices. As for now, supports keyboards and numpads."""

    default_name_mapping = {"KEY_KPENTER":"KEY_ENTER", "KEY_PAGEUP":"KEY_F3", "KEY_PAGEDOWN":"KEY_F4"}
    supports_key_states = True
    supports_held_state = True

    def __init__(self, path=None, name=None, **kwargs):
        """Initialises the ``InputDevice`` object.

        Kwargs:

            * ``path``: path to the input device. If not specified, you need to specify ``name``.
            * ``name``: input device name

        """
        if not name and not path: #No necessary arguments supplied
            raise TypeError("HID device driver: expected at least path or name; got nothing. =(")
        self.path = path
        self.name = name
        InputSkeleton.__init__(self, mapping = [], **kwargs)
        self.hid_device_error_filter = False

    @property
    def status_available(self):
        return True

    @status_available.setter
    def status_available(self, value):
        pass

    def set_available_keys(self):
        if hasattr(self, 'device'):
            keys = [ecodes.keys[x] for x in self.device.capabilities()[ecodes.EV_KEY] \
                             if isinstance(ecodes.keys[x], basestring) ]
            self.available_keys = keys
        else:
            self.available_keys = None

    def detect_device_path(self):
        if not self.path:
            self.path = get_path_by_name(self.name)
        if not self.name:
            self.name = get_name_by_path(self.path)
        if not self.name and not self.path: #Seems like nothing was found by get_input_devices
            raise IOError("Device not found by path and no name was provided")

    def init_hw(self):
        self.detect_device_path()
        self.device = HID(self.path)
        self.device.grab() #Can throw exception if already grabbed
        return True

    def runner(self):
        """Blocking event loop which just calls supplied callbacks in the keymap."""
        while not self.stop_flag:
            if not self.check_connection():
                # Looping while the device is not found
                sleep(self.connection_check_sleep)
                continue
            try:
                event = self.device.read_one()
                self.hid_device_error_filter = False
            except (IOError, AttributeError) as e:
                if not self.hid_device_error_filter:
                    logger.exception("Error while reading from the HID device {}!".format(self.path))
                    self.hid_device_error_filter = True
                if isinstance(e, IOError) and e.errno == 11:
                    #raise #Uncomment only if you have nothing better to do - error seems to appear at random
                    continue
                else:
                    self.connected.clear()
            except Exception as e:
                logger.exception("Error while reading from the HID device {}!".format(self.path))
                self.connected.clear()
            else:
                self.process_event(event)
                sleep(0.01)

    def process_event(self, event):
        if event is not None and event.type == ecodes.EV_KEY:
            key = ecodes.keys[event.code]
            value = event.value
            if self.enabled:
                key = self.keycode_mapping.get(key, key)
                self.map_and_send_key(key, state = value)

    def atexit(self):
        InputSkeleton.atexit(self)
        try:
            self.device.ungrab()
        except:
            pass


if __name__ == "__main__":
    print("Available device names:")
    print([dev.name for dev in get_input_devices()])
    #id = InputDevice(name = get_input_devices()[0].name, threaded=False)
    #id.runner()
