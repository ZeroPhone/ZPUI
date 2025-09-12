from threading import Event, Thread
from traceback import format_exc
from functools import wraps
from subprocess import call
from time import sleep
import sys
import os

from zpui_lib.apps import ZeroApp
from zpui_lib.ui import Menu, Printer, PrettyPrinter, Canvas
from zpui_lib.helpers import ExitHelper, local_path_gen, setup_logger, remove_left_failsafe, BackgroundRunner

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

    def read_file(self, file):
        with open(os.path.join(self.fw_dir, file), 'r') as f:
            c = f.read()
        return c.rstrip()

    def try_read_file(self, file):
        try:
            return self.read_file(file)
        except:
            logger.exception("Error when reading file {}".format(file))
            return None

    def try_detect_driver(self):
        try:
            self.read_file(self.batt_volt_path)
        except:
            logger.exception("Beepy driver is not loaded?")
            return False
        return True

    def can_load(self):
        return True # debug
        return self.driver_found # to be used in the future

    def get_backlight(self):
        # not all driver versions support reading the backlight level
        return self.try_read_file(self.backlight_path)

    def get_battery(self):
        # not all driver versions support reading the backlight level
        return self.try_read_file(self.batt_volt_path)

    def on_start(self):
        def ch():
            backlight = self.get_backlight()
            backlight_str = "Backlight: {}".format(backlight) if backlight != None else "Backlight"
            battery = self.get_battery()
            battery_str = "Battery: {}V".format(battery) if battery != None else "Battery V: Uknown"
            mc = [
                  [backlight_str],
                  [battery_str],
                  #["Keypad presence", self.test_keypad_presence],
                  #["I2C GPIO expander", self.test_i2c_gpio],
                  #["Screen", self.test_screen],
                  #["Keypad", self.test_keypad],
                  #["Charger", self.test_charger],
                  #["RGB LED", self.test_rgb_led],
                  #["USB port", self.test_usb_port],
                  #["Headphone jack", self.test_headphone_jack]
            ]
            return mc
        Menu([], self.i, self.o, contents_hook=ch, name="Beepy control app main menu").activate()

    """
    @needs_i2c_gpio_expander
    def test_charger(self):
        #Testing charging detection
        PrettyPrinter("Testing charger detection", self.i, self.o, 1)
        from zerophone_hw import Charger
        charger = Charger()
        eh = ExitHelper(self.i, ["KEY_LEFT", "KEY_ENTER"]).start()
        if charger.connected():
            PrettyPrinter("Charging, unplug charger to continue \n Enter to bypass", None, self.o, 0)
            while charger.connected() and eh.do_run():
                sleep(1)
        else:
            PrettyPrinter("Not charging, plug charger to continue \n Enter to bypass", None, self.o, 0)
            while not charger.connected() and eh.do_run():
                sleep(1)

    @needs_i2c_gpio_expander
    def test_rgb_led(self):
        PrettyPrinter("Testing RGB LED", self.i, self.o, 1)
        from zerophone_hw import RGB_LED
        led = RGB_LED()
        for color in ["red", "green", "blue"]:
            led.set_color(color)
            Printer(color.center(self.o.cols), self.i, self.o, 3)
        led.set_color("none")

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

    def test_headphone_jack(self):
        #Testing audio jack sound
        PrettyPrinter("Testing audio jack", self.i, self.o, 1)
        if self.br:
            if self.br.running:
                PrettyPrinter("Audio jack test music not yet downloaded, waiting...", None, self.o, 0)
                eh = ExitHelper(self.i, ["KEY_LEFT", "KEY_ENTER"]).start()
                while self.br.running and eh.do_run():
                    sleep(0.1)
                if eh.do_exit():
                    return
            elif self.br.failed:
                PrettyPrinter("Failed to download test music!", self.i, self.o, 1)
        disclaimer = ["Track used:" "", "Otis McDonald", "-", "Otis McMusic", "YT AudioLibrary"]
        Printer([s.center(self.o.cols) for s in disclaimer], self.i, self.o, 3)
        PrettyPrinter("Press C1 to restart music, C2 to continue testing", self.i, self.o)
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.play()
        continue_event = Event()
        def restart():
            pygame.mixer.music.stop()
            pygame.mixer.init()
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play()
        def stop():
            pygame.mixer.music.stop()
            continue_event.set()
        self.i.clear_keymap()
        self.i.set_callback("KEY_F1", restart)
        self.i.set_callback("KEY_F2", stop)
        self.i.set_callback("KEY_ENTER", stop)
        continue_event.wait()
    """
