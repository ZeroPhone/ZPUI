from threading import Thread, Event
from time import sleep
from datetime import datetime

def activate_backlight_wrapper(func):
    def wrapper(display, *args, **kwargs):
        if "backlight_only_on_new" in kwargs:
           b = kwargs.pop("backlight_only_on_new")
           if b:
               if not hasattr(display, "trigger_backlight_on_change"):
                   print("Backlight only on change requested but display driver doesn't have a change check hook!")
               elif not display.trigger_backlight_on_change(display, func.__name__, *args, **kwargs):
                   # No need to re-trigger backlight at the moment, return
                   # if the image keeps being the same, it will just timeout
                   # Also, assuming that trigger_backlight_on_change implies
                   # the display state actually won't be changed by this call
                   # if it were to be executed => we don't need to update
                   # current_image and so on
                   return
        display.enable_backlight()
        display._backlight_active.set()
        result = func(display, *args, **kwargs)
        if display._backlight_interval and display._bl_thread is None:
            display.start_backlight_thread()
        return result
    return wrapper

def enable_backlight_wrapper(func):
    def wrapper(display, *args, **kwargs):
        if display._backlight_enabled == False:
            display._backlight_enabled = True
            return func(display, *args, **kwargs)
        return None
    return wrapper

def disable_backlight_wrapper(func):
    def wrapper(display, *args, **kwargs):
        if display._backlight_enabled == True:
            display._backlight_enabled = False
            return func(display, *args, **kwargs)
        return None
    return wrapper

class BacklightManager(object):
    _last_active = datetime.now()
    _backlight_enabled = False
    _backlight_active = Event()

    def init_backlight(self, backlight_active_level=True, backlight_pin = None, backlight_interval = None, **kwargs):
        self._backlight_active_level = backlight_active_level
        self._backlight_pin = backlight_pin
        if self._backlight_pin:
            import RPi.GPIO as GPIO
            self._bl_gpio = GPIO
            self._bl_gpio.setmode(self._bl_gpio.BCM)
            self._bl_gpio.setwarnings(False)
            self._bl_gpio.setup(self._backlight_pin, self._bl_gpio.OUT)
        self._backlight_interval = backlight_interval
        if self._backlight_interval:
            self.start_backlight_thread()

    def set_backlight_callback(self, obj):
        obj.backlight_cb = self.activate_backlight

    @activate_backlight_wrapper
    def activate_backlight(self):
        """Returns True when backlight has been activated, False if 
        backlight timer is disabled or backlight is already enabled"""
        return self._backlight_interval and self._bl_thread is None

    @enable_backlight_wrapper
    def enable_backlight(self):
        if self._backlight_pin:
            self._bl_gpio.output(self._backlight_pin, self._backlight_active_level)

    @disable_backlight_wrapper
    def disable_backlight(self):
        if self._backlight_pin:
            self._bl_gpio.output(self._backlight_pin, not self._backlight_active_level)

    def start_backlight_thread(self):
        self._bl_thread = Thread(target=self.backlight_manager, name="Screen backlight manager thread")
        self._bl_thread.daemon = True
        self._bl_thread.start()

    def backlight_manager(self):
        while True:
            if self._backlight_active.isSet():
                self._backlight_active.clear()
                self._last_active = datetime.now()
            elif (datetime.now() - self._last_active).total_seconds() >self._backlight_interval and self._backlight_enabled:
                self.disable_backlight()
                self._bl_thread = None
                return
            sleep(float(self._backlight_interval)/2) #Doesn't need to be done much often unless you need your backlight to be super precise. /2 is minimum though. 1 cycle to clear the flag and 1 cycle to disable backlight
