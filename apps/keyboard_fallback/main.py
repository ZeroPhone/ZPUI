from time import sleep
from threading import Event

from ui import Canvas, Refresher
from ui.base_ui import BaseUIElement
from apps import ZeroApp
from zpui_lib.helpers import ExitHelper, setup_logger, remove_left_failsafe, read_or_create_config, local_path_gen, save_config_method_gen

logger = setup_logger(__name__, "info")

from __main__ import input_device_manager as device_manager

zerophone_hw = False
try:
    from zerophone_hw import USB_DCDC
except:
    zerophone_hw = False
else:
    zerophone_hw = True


class KeyboardFallbackApp(ZeroApp):

    do_not_activate_events = ["usb_keyboard_connected"]

    def can_load(self):
        return False, "app mothballed until it's updated and ready to be used"

    def init_app(self):
        self.active = Event()
        self.pop_on_event = Event()
        self.pop_on_event.set()
        self.c = Canvas(self.o)
        device_manager.register_monitor_callback(self.process_dm_event)
        self.i.set_streaming(self.deactivate)
        self.state = None
        self.status_image = "No image"
        self.r = Refresher(self.get_status_image, self.i, self.o, name="Keyboard fallback status refresher")

    def deactivate(self, keyname, *args, **kwargs):
        # Upon receiving *any* key when active, it's our hint from the user
        # to not appear again ;-P
        # Unless the keyboard was just connected, of course
        if self.state == "usb_keyboard_connected":
            self.r.deactivate()
            self.context.signal_background()
        else:
            self.pop_on_event.clear()

    def go_into_foreground(self):
        if not self.pop_on_event.is_set():
            return False
        return self.context.request_switch()

    def process_dm_event(self, event):
        self.c.clear()
        self.state = event
        if not self.context.is_active() and self.pop_on_event.is_set() \
          and event not in self.do_not_activate_events:
            if not self.go_into_foreground():
                return
        if event == "usb_keyboard_connected":
            self.c.centered_text("USB kb connected")
        elif event == "custom_i2c_disconnected":
            self.c.centered_text("Keypad not found!")
            try:
                dcdc = USB_DCDC()
                dcdc.on()
            except:
                logger.exception("Can't turn the ZP USB DC-DC on!")
        elif event == "looking_for_usb_keyboard":
            self.c.centered_text("Keypad not found!", ch=16)
            self.c.centered_text("Looking for USB kb")
        elif event == "usb_keyboard_found":
            self.c.centered_text("USB keyboard found")
        elif event == "usb_keyboard_disconnected":
            self.c.centered_text("USB kb disconnected!")
        self.status_image = self.c.get_image()
        if self.state == "usb_keyboard_connected":
            sleep(2)
            if self.state == "usb_keyboard_connected":
                self.r.deactivate()
                self.context.signal_background()

    def set_context(self, c):
        self.context = c
        c.set_target(self.show_status)

    def get_status_image(self):
        return self.status_image

    def show_status(self):
        self.r.activate()
