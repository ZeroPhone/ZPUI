from threading import Event, Thread
from traceback import format_exc
from functools import wraps
from subprocess import call
from time import sleep
import sys
import os

from apps import ZeroApp
from ui import Menu, Printer, PrettyPrinter, Canvas
from zpui_lib.helpers import ExitHelper, local_path_gen, setup_logger, remove_left_failsafe, BackgroundRunner

from smbus import SMBus

logger = setup_logger(__name__, "warning")

music_filename = "test.mp3"
local_path = local_path_gen(__name__)
music_path = local_path(music_filename)


def needs_i2c_gpio_expander(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.expander_ok:
            self.test_i2c_gpio()
        if self.expander_ok:
            return func(self, *args, **kwargs)
        else: # Won't execute the function at all if expander is not found
            return False
    return wrapper


class ZPTestApp(ZeroApp):

    menu_name = "Test ZeroPhone"
    music_url = "http://wiki.zerophone.org/images/b/b5/Otis_McMusic.mp3"
    br = None

    expander_ok = False

    def __init__(self, *args, **kwargs):
        ZeroApp.__init__(self, *args, **kwargs)
        if music_filename not in os.listdir(local_path('.')):
            self.br = BackgroundRunner(self.download_music)
            self.br.run()

    def download_music(self):
       logger.debug("Downloading music for hardware test app!")
       call(["wget", self.music_url, "-O", music_path])

    def on_start(self):
        mc = [["Full test", self.full_test],
              ["Keypad presence", self.test_keypad_presence],
              ["I2C GPIO expander", self.test_i2c_gpio],
              ["Screen", self.test_screen],
              ["Keypad", self.test_keypad],
              ["Charger", self.test_charger],
              ["RGB LED", self.test_rgb_led],
              #["USB port", self.test_usb_port],
              ["Headphone jack", self.test_headphone_jack]]
        Menu(mc, self.i, self.o, name="Hardware test app main menu").activate()

    def full_test(self):
        try:
            self.test_keypad_presence()
            self.test_i2c_gpio()
            self.test_screen()
            self.test_keypad()
            self.test_charger()
            self.test_rgb_led()
            self.test_usb_port()
            self.test_headphone_jack()
        except:
            logger.exception("Failed during full self-test")
            exc = format_exc()
            PrettyPrinter(exc, self.i, self.o, 10)
        else:
            PrettyPrinter("Self-test passed!", self.i, self.o, 3, skippable=False)

    def test_keypad_presence(self):
        #Checking keypad controller - 0x12 should answer
        bus = SMBus(1)
        try:
            bus.read_byte(0x12)
        except IOError:
            PrettyPrinter("Keypad does not respond!", self.i, self.o)
        else:
            PrettyPrinter("Keypad found!", self.i, self.o)

    def test_i2c_gpio(self):
        #Checking IO expander - 0x20 should raise IOError with busy errno
        self.expander_ok = False
        bus = SMBus(1)
        try:
            bus.read_byte(0x20)
        except IOError as e:
            if e.errno == 16:
                PrettyPrinter("IO expander OK!", self.i, self.o)
                self.expander_ok = True
            elif e.errno == 121:
                PrettyPrinter("IO expander not found!", self.i, self.o)
        else:
            PrettyPrinter("IO expander driver not loaded!", self.i, self.o)

    def test_screen(self):
        # Testing the screen - drawing a "crosshair" to test screen edges and lines
        c = Canvas(self.o)
        c.line((0, 0, 10, 0))
        c.line(("-1", 0, "-10", 0))
        c.line((0, "-1", 10, "-1"))
        c.line(("-1", "-1", "-10", "-1"))
        c.line((0, 0, 0, 10))
        c.line((0, "-1", 0, "-10"))
        c.line(("-1", 10, "-1", 0))
        c.line(("-1", "-1", "-1", "-10"))
        c.line((0, 0, "-1", "-1"))
        c.line((0, "-1", "-1", 0))
        eh = ExitHelper(self.i, ["KEY_ENTER", "KEY_LEFT"]).start()
        c.display(); sleep(1)
        for x in range(30):
            if eh.do_run():
                if x % 10 == 0:
                    c.invert(); c.display()
                sleep(0.1)
            else:
                break
        # Filling the screen (still using the same ExitHelper)
        c = Canvas(self.o)
        for x in range(60):
            if eh.do_run():
                if x % 20 == 0:
                    c.invert(); c.display()
                sleep(0.1)
            else:
                break

    def test_keypad(self):
        #Launching key_test app from app folder, that's symlinked from example app folder
        PrettyPrinter("Testing keypad", self.i, self.o, 1)
        remove_left_failsafe(self.i)
        import key_test
        key_test.init_app(self.i, self.o)
        key_test.callback()

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
