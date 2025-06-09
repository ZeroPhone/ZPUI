from threading import Thread
from time import sleep

from zpui_lib.helpers import setup_logger

# If evdev is not available, mark it as 'None' so that it's known as unavailable
try:
    import evdev
except ImportError:
    evdev = None

logger = setup_logger(__name__, "warning")

def get_input_devices():
    """Returns list of all the available InputDevices"""
    from evdev import list_devices
    devices = []
    for fn in evdev.list_devices():
        try:
            devices.append(evdev.InputDevice(fn))
        except:
            logger.exception("Error while listing a HID device {}".format(fn))
            pass
    return devices


class DeviceManager():
    def __init__(self, i):
        self.i = i
        self.driver_storage = {}
        self.monitor_cbs = []
        self.start_monitor_loops()
        self.unconnectable_keyboards = []

    def register_monitor_callback(self, cb):
        self.monitor_cbs.append(cb)

    def remove_monitor_callback(self, cb):
        self.monitor_cbs.remove(cb)

    def notify_event(self, event):
        if self.monitor_cbs:
            logger.info("Event: {}, sending it to callbacks".format(event))
        else:
            logger.info("Event: {} (no monitor callbacks set)".format(event))
        for cb in self.monitor_cbs:
            try:
                cb(event)
            except:
                logger.exception("Callback {} ({}) failed to receive event!".format(cb, cb.__name__))

    def get_drivers(self):
        return self.driver_storage

    def add_driver(self, path=None, name=None, dtype="hid"):
        if dtype not in ["hid"]:
            raise ValueError("Types other than 'hid' are not supported- asked for {}!".format(dtype))
        if dtype == "hid":
            from drivers.hid import InputDevice as HIDDriver
            driver = HIDDriver(path=path, name=name)
        dname = self.i.attach_driver(driver)
        self.driver_storage[dname] = driver
        return dname

    def remove_driver(self, name):
        driver = self.driver_storage.pop(name)
        self.i.detach_driver(name)
        driver.atexit()

    def start_monitor_loops(self):
        # Only start the "wait for USB keyboard on custom i2c device" loop
        # if custom i2c devices are actually present and evdev lib is installed
        ci_drivers = self.get_custom_i2c_drivers()
        if len(ci_drivers) > 0 and evdev is not None:
            self.start_ukouk_thread()

    def start_ukouk_thread(self):
        self.ukouk_thread = Thread(target=self.connect_usb_keyboard_on_unresponsive_keypad_loop, \
                                name="'connect USB keyboard on unresponsive keypad' monitor thread")
        self.ukouk_thread.daemon = True
        self.ukouk_thread.start()

    driver_ok_sleep = 5
    usb_keyboard_not_detected_sleep = 3
    usb_keyboard_connected_sleep = 1

    def connect_usb_keyboard_on_unresponsive_keypad_loop(self):
        ci_drivers = self.get_custom_i2c_drivers()
        driver = ci_drivers[0] # Can't wait until I think of a better heuristic lol
        while True:
            if driver.connected.is_set() is not True:
                print(driver.connected.is_set())
                self.notify_event("custom_i2c_disconnected")
                usb_keyboard = None
                while usb_keyboard is None and not driver.connected.is_set():
                    self.notify_event("looking_for_usb_keyboard")
                    usb_keyboard = self.detect_usb_keyboard()
                    if usb_keyboard is None:
                        sleep(self.usb_keyboard_not_detected_sleep)
                if driver.connected.is_set(): # Driver is active again
                    self.notify_event("custom_i2c_connected_back")
                    continue
                else: # Driver still not active and keyboard was found
                    self.notify_event("usb_keyboard_found")
                    driver_name = self.connect_usb_keyboard(usb_keyboard.name)
                    if driver_name:
                        self.notify_event("usb_keyboard_connected")
                        while self.i.drivers[driver_name].connected.is_set(): # idling while driver is connected
                            sleep(self.usb_keyboard_connected_sleep)
                        self.notify_event("usb_keyboard_disconnected")
                        self.remove_driver(driver_name)
                    else:
                        self.notify_event("usb_keyboard_failed_to_connect")
                        self.unconnectable_keyboards.append(usb_keyboard.name)
            else: # driver OK
                sleep(self.driver_ok_sleep)

    def detect_usb_keyboard(self):
        hid_devices = get_input_devices()
        usb_keyboards = [hid_dev for hid_dev in hid_devices if hid_dev.name not in self.unconnectable_keyboards]
        return usb_keyboards[0] if usb_keyboards else None # again, needs a better heuristic

    def connect_usb_keyboard(self, usb_keyboard):
        try:
            driver_name = self.add_driver(name=usb_keyboard, dtype="hid")
        except:
            logger.exception("Failed to attach USB keyboard {}:".format(usb_keyboard))
            return False
        else:
            return driver_name

    def keypad_unresponsive(self):
        self.notify_event("keypad_unresponsive")

    def get_custom_i2c_drivers(self):
        custom_i2c_drivers = [driver for name, driver in self.i.drivers.items() if name.startswith("custom_i2c")]
        return custom_i2c_drivers
