from threading import Event, Thread
from traceback import format_exc
from functools import wraps
from subprocess import call
from time import sleep
import sys
import os

from zpui_lib.apps import ZeroApp
from zpui_lib.ui import Menu, Printer, PrettyPrinter, Canvas, IntegerAdjustInput
from zpui_lib.helpers import ExitHelper, local_path_gen, setup_logger, remove_left_failsafe, BackgroundRunner, get_platform


from smbus import SMBus

logger = setup_logger(__name__, "warning")

music_filename = "test.mp3"
local_path = local_path_gen(__name__)
music_path = local_path(music_filename)


class BeepyApp(ZeroApp):

    menu_name = "Beepy control"

    fw_dir = "/sys/firmware/beepy/"
    batt_per_path = "battery_percent"
    batt_raw_path = "battery_raw"
    batt_volt_path = "battery_volts"
    usb_mouse_path = "usb_mouse"
    usb_keyboard_path = "usb_keyboard"
    mux_fusb_path = "mux_fusb"
    charger_enable_path = "charger_enabled"
    backlight_path = "keyboard_backlight"

    """
    root@bepis:~# ls /sys/firmware/beepy/
    battery_percent  battery_raw  battery_volts  charger_enabled  charger_power
    fw_update  fw_version  keyboard_backlight  last_keypress
    led  led_blue  led_green  led_red  mux_fusb  mux_usb
    rewake_timer  startup_reason  usb_keyboard  usb_mouse  vibromotor
    """

    def init_app(self):
        self.driver_found = self.try_detect_driver()

    def set_context(self, c):
        self.context = c

    def read_file(self, file):
        with open(os.path.join(self.fw_dir, file), 'r') as f:
            c = f.read()
        return c.rstrip()

    def try_read_file(self, file):
        try:
            return self.read_file(file)
        except:
            if "emulator" in get_platform():
                logger.debug("Error when reading file {}".format(file))
                return None # no error message needed
            logger.exception("Error when reading file {}".format(file))
            return None

    def try_detect_driver(self):
        try:
            self.read_file(self.batt_volt_path)
        except:
            if "emulator" in get_platform():
                logger.info("Beepy driver not found but emulator detected, loading the app anyway")
            else:
                logger.exception("Beepy driver is not loaded?")
            return False
        return True

    def can_load(self):
        if "emulator" in get_platform():
            return True # for debug purposes
        else:
            return self.driver_found

    def set_file_binary(self, path, state):
        if state not in ["0", "1"]:
            state = str(int(state))
        with open(os.path.join(self.fw_dir, path), "w") as f:
            logger.debug("Writing {} into {}".format(repr(state), os.path.join(self.fw_dir, path)))
            f.write(state)

    def backlight_set(self):
        current_backlight_level = int(self.backlight_get()) if self.backlight_get() is not None else 120
        number_input = IntegerAdjustInput(current_backlight_level, self.i, self.o, interval=10, max=255, min=0)
        backlight_level =  number_input.activate()
        if backlight_level != None:
            logger.info("Setting backlight level to {}".format(backlight_level))
            with open(os.path.join(self.fw_dir, "keyboard_backlight"), "w") as f:
                f.write(str(backlight_level))

    def backlight_get(self):
        # not all driver versions support reading the backlight level
        return self.try_read_file(self.backlight_path)

    def usb_mouse_get(self):
        return self.try_read_file(self.usb_mouse_path)

    def usb_keyboard_get(self):
        return self.try_read_file(self.usb_keyboard_path)

    def usb_mouse_set(self, state):
        return self.set_file_binary(self.usb_mouse_path, state)

    def usb_keyboard_set(self, state):
        return self.set_file_binary(self.usb_keyboard_path, state)

    def get_battery(self):
        # not all driver versions support reading the backlight level
        return self.try_read_file(self.batt_volt_path)

    def mux_fusb_get(self):
        state = self.try_read_file(self.mux_fusb_path)
        if state == None: return None
        return bool(int(state)) # convert "1"/"0" to True/False

    def mux_fusb_toggle(self):
        state = self.mux_fusb_get()
        new_state = not state
        logger.info("Setting FUSB mux state from {} to {}".format(str(int(state)), str(int(new_state))))
        self.set_file_binary(self.mux_fusb_path, new_state)

    def mux_fusb_set(self, state):
        logger.info("Setting FUSB mux state to {}".format(str(int(state))))
        self.set_file_binary(self.mux_fusb_path, state)

    def charger_enable_get(self):
        state = self.try_read_file(self.charger_enable_path)
        if state == None: return None
        return bool(int(state)) # convert "1"/"0" to True/False

    def charger_enable_toggle(self):
        state = self.charger_enable_get()
        new_state = not state
        logger.info("Setting FUSB mux state from {} to {}".format(str(int(state)), str(int(new_state))))
        self.set_file_binary(self.charger_enable_path, new_state)

    def charger_enable_set(self, state):
        logger.info("Setting FUSB mux state to {}".format(str(int(state))))
        self.set_file_binary(self.charger_enable_path, state)

    def usb_input_mode_graphic(self):
        c = Canvas(self.o)
        # assuming graphic display support cuz Beepy has it
        # but it can be 320x240, not just 400x240
        """ # reconsidered this mode because the characters entered might impact the currently-connected system. no need to thank me :3
        c.centered_text("To exit keyboard/mouse mode, type", oy=-24, font=("Fixedsys62.ttf", 16))
        c.centered_text("\"owo whats this\"", font=("Fixedsys62.ttf", 16))
        c.centered_text("(with or without spaces)", oy=24,  font=("Fixedsys62.ttf", 16))"""
        c.centered_text("To exit keyboard/mouse mode, press", oy=-24, font=("Fixedsys62.ttf", 16))
        c.centered_text("SHIFT and SYM", font=("Fixedsys62.ttf", 16))
        c.centered_text("(both together)", oy=24,  font=("Fixedsys62.ttf", 16))
        c.display()

    def usb_input_mode(self):
        # we're fucking with input, let's be extra careful
        try:
            from evdev import InputDevice as HID, list_devices
        except ImportError:
            logger.exception("Cannot import the necessary libraries - very weird, they should be available on a Beepy target!")
            return
        init_success = False
        try:
            self.usb_mouse_set(True)
            self.usb_keyboard_set(True)
            init_success = True
        except:
            logger.exception("Failure during USB keyboard/mouse mode init!")
        else:
            logger.info("USB keyboard&mouse mode init successful")
        if init_success:
            # only execute All This Code if the init has been successful
            zpui = self.context.request_zpui()
            try:
                # we need to:
                # output a notification on the screen
                self.usb_input_mode_graphic()
                # suspend ZPUI
                zpui.suspend()
                # grab the keyboard&mouse here
                # getting driver name
                drivers = zpui.input_processor.drivers
                fitting_drivers = [driver for name,driver in drivers.items() if name.startswith("beepy_hid")]
                if not fitting_drivers:
                    raise ValueError("No beepy_hid driver found to grab, cancelling")
                if len(fitting_drivers) > 1:
                    logger.warning("More than one beepy_hid driver found, using the first one: {}".format(fitting_drivers))
                # ain't gonna process multiple drivers yet, so,
                # picking the first one if multiple are found, SOMEHOW
                driver = fitting_drivers[0]
                logger.info("Using input driver {}".format(driver))
                # driver HID device name
                hid_name = driver.name
                hid_path = driver.path
                device = None
                for fn in list_devices():
                    if fn == hid_path:
                        device = HID(fn)
                        break
                if device:
                    # device is now a HID device - let's loop on its keycodes until a magic sequence of keystrokes appears!
                    try:
                        status = self.wait_for_held_keys(device)
                        if status[0] != True:
                            logger.error("Failure while capturing HID events: {}".format(status[1]))
                    except:
                        logger.exception("Uncaught exception during USB event processing!")
                else:
                    logger.error("Beepy HID device not currently connected? o_o")
            except:
                logger.exception("Failure during USB keyboard&mouse mode!")
            finally:
                zpui.unsuspend()
        # cleanup, either which way
        try:
            self.usb_mouse_set(False)
        except:
            if not "emulator" in get_platform():
                logger.exception("Failure setting USB mouse!")
        try:
            self.usb_keyboard_set(False)
        except:
            if not "emulator" in get_platform():
                logger.exception("Failure setting USB keyboard!")
        return # this code tries its best
        # todo: maybe start a background thread that tries restoring correct mouse/keyboard mode until it succeeds?
        # depends on whether it gives IOError when RP2040 is not responding, ig.
        # write and read back to confirm? idk it'll probably work it's fiiiiiine =D

    def wait_for_held_keys(self, device):
        # device is now a HID device - let's loop on its keycodes until a magic sequence of keystrokes appears!
        # sure hope this code works well lol
        from evdev import ecodes
        pressed_keys = []
        self.do_scan = True # we might want to expose this externally later or add a failsafe hook??
        # maybe in the future we can detect USB cable unplug or such! that'd be so cool
        try:
            device.grab()
            while self.do_scan:
                event = device.read_one()
                if event is not None and event.type == ecodes.EV_KEY:
                    key = ecodes.keys[event.code]
                    if event.value == 1: # pressed
                        if key not in pressed_keys: pressed_keys.append(key)
                    elif event.value == 0: # released
                        if key in pressed_keys: pressed_keys.remove(key)
                    if "KEY_RIGHTALT" in pressed_keys and "KEY_LEFTSHIFT" in pressed_keys:
                        # yippie! let's try to ungrab now
                        try:
                            device.ungrab()
                        except:
                            tb += format_exc()
                            return (False, tb)
                        else:
                            return (True,) # ungrab successful, all is good
                if event == None:
                    sleep(0.2)
        except:
            tb = format_exc()
            try:
                device.ungrab()
            except:
                # whoops ungrab fail too, let's just append
                tb += '\n'
                tb += format_exc()
            return (False, tb)
        else: # normal exit?? idk let's see
            try:
                device.ungrab()
            except:
                # whoops ungrab fail too, let's just append
                tb += '\n'
                tb = format_exc()
                return (False, tb)
            return (True,)

    def on_start(self):
        def ch():
            backlight = self.backlight_get()
            backlight_str = "Backlight: {}".format(backlight) if backlight != None else "Backlight"
            battery = self.get_battery()
            battery_str = "Battery: {}V".format(battery) if battery != None else "Battery V: Unknown"
            usb_keyboard = self.usb_keyboard_get() != None # (True if not None, since None means an exception has occured)
            mux_fusb = self.mux_fusb_get()
            charger_enabled = self.charger_enable_get()
            mc = [
                  [backlight_str, self.backlight_set],
                  [battery_str],
            ]
            if usb_keyboard != None:
                mc.append(["USB input mode", self.usb_input_mode])
            if charger_enabled != None:
                state = "on" if charger_enabled == True else "off"
                mc.append(["Charging: {}".format(state), self.charger_enable_toggle])
            if mux_fusb != None:
                state = "Pi Zero" if mux_fusb == True else "RP2040"
                mc.append(["FUSB302 mux: {}".format(state), self.mux_fusb_toggle])
            return mc
        if not hasattr(self, "m"):
            self.m = Menu([], self.i, self.o, contents_hook=ch, name="Beepy control app main menu")
        self.m.activate()

    """
    @needs_i2c_gpio_expander
    def test_usb_port(self):
        from zerophone_hw import USB_DCDC
        eh = ExitHelper(self.i, ["KEY_LEFT", "KEY_ENTER"]).start()
        PrettyPrinter("Press Enter to test USB", None, self.o, 0)
        counter = 5
        for x in range(50):
            if eh.do_run():
                if x % 10 == 0: counter -= 1
                sleep(0.1)
            else:
                break
        if counter > 0:
            PrettyPrinter("Insert or remove a USB device \n press Enter to skip", None, self.o, 0)
            dcdc = USB_DCDC()
            dcdc.on()
            # wait for devices to enumerate? probably not
            # if we don't, this hack might allow detecting a plugged device and proceeding with it
            # so the test succeeds without any interaction on user's part
            #orig_usb_devs = get_usb_devs()
            #new_usb_devs = orig_usb_devs
            #eh = ExitHelper(self.i).start()
            #while eh.do_run() and orig_usb_devs != new_usb_devs:
            #    sleep(1)
            #    new_usb_devs = get_usb_devs()
            #if eh.do_stop():
            #    return
            #if len(new_usb_devs) < len(orig_usb_devs):
            #    Printer("USB device(s) removed!", i, o, 3)
            #elif len(new_usb_devs) > len(orig_usb_devs):
            #    Printer("New USB device(s) found!", i, o, 3)
            #elif len(new_usb_devs) == len(orig_usb_devs):
            #    logger.warning("USB device test weirdness: len({}) == len({})".format(orig_usb_devs, new_usb_devs))
            #    Printer("Different USB device plugged?", i, o, 3)
    """
