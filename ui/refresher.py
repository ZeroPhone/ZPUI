from time import sleep
from functools import wraps
from traceback import print_exc

import PIL

from ui.number_input import IntegerAdjustInput
from ui.utils import to_be_foreground
from ui.base_ui import BaseUIElement, internal_callback_in_background
from helpers import setup_logger

logger = setup_logger(__name__, "info")


class RefresherExitException(Exception):
    pass


class Refresher(BaseUIElement):
    """
    A Refresher allows you to update the screen on a regular interval.
    All you need is to provide a function that'll return the text/image you want to display;
    that function will then be called with the desired frequency and the display
    will be updated with whatever it returns.
    """

    def __init__(self, refresh_function, i, o, refresh_interval=1, keymap=None, name="Refresher", **kwargs):
        """Initialises the Refresher object.

        Args:

            * ``refresh_function``: a function which returns data to be displayed on the screen upon being called, in the format accepted by ``screen.display_data()`` or ``screen.display_image()``. To be exact, supported return values are:

              * Tuples and lists - are converted to lists and passed to ``display_data()``
              * Strings - are converted to a single-element list and passed to ``display_data()``
              * `PIL.Image` objects - are passed to ``display_image()``

            * ``i``, ``o``: input&output device objects

        Kwargs:

            * ``refresh_interval``: Time between display refreshes (and, accordingly, ``refresh_function`` calls).
            * ``keymap``: Keymap entries you want to set while Refresher is active.
              * By default, KEY_LEFT deactivates the Refresher, if you want to override it, make sure that user can still exit the Refresher.
            * ``name``: Refresher name which can be used internally and for debugging.

        """
        self.custom_keymap = keymap if keymap else {}
        BaseUIElement.__init__(self, i, o, name, input_necessary=False, **kwargs)
        self.set_refresh_interval(refresh_interval)
        self.set_refresh_function(refresh_function)
        self.calculate_intervals()

    @property
    def is_active(self):
        return self.in_background

    def pause(self):
        """
        Pauses the refresher, not allowing it to print anything on the screen
        while it's paused.
        """
        self.in_foreground = False

    def resume(self):
        """
        Resumes the refresher after it's been paused, allowing it to continue
        printing things on the screen. Refreshes the screen when it's called.
        """
        if not self.in_foreground:
            self.to_foreground()

    def background_if_inactive(self):
        """
        If the UI element hasn't been launched yet, launches it in background
        and waits until it's fully running. Otherwise, resumes the UI element.
        """
        if not self.is_active:
            self.run_in_background()
            self.wait_for_active()
        else:
            self.resume()

    def wait_for_active(self, timeout=100):
        """
        If the UI element hasn't been launched yet, launches it in background
        and waits until it's fully running.
        """
        counter = 0
        while not self.is_active:
            sleep(0.1)
            counter += 1
            if counter == timeout:
                raise ValueError("Waiting for {} to be active - never became active!".format(self.name))

    def set_refresh_interval(self, new_interval):
        """Allows setting Refresher's refresh intervals after it's been initialized"""
        #interval for checking the in_background property in the activate()
        #when refresh_interval is small enough, is the same as refresh_interval
        if new_interval == 0:
            raise ValueError("Refresher refresh_interval can't be 0 ({})".format(self.name))
        self.refresh_interval = new_interval
        self.sleep_time = 0.1 if new_interval > 0.1 else new_interval
        self.calculate_intervals()

    def set_refresh_function(self, refresh_function):
        if isinstance(refresh_function, RefresherView):
            refresh_function.init(self.o)
        self.refresh_function = refresh_function

    def calculate_intervals(self):
        """Calculates the sleep intervals of the refresher, so that no matter the
        ``refresh_interval``, the refresher is responsive. Also, sets the counter to zero."""
        #in_background of the refresher needs to be checked approx. each 0.1 second,
        #since users expect the refresher to exit almost instantly
        iterations_before_refresh = self.refresh_interval/self.sleep_time
        if iterations_before_refresh < 1:
            logger.warning("{}: self.refresh_interval is smaller than self.sleep_time!".format(self.name))
            #Failsafe
            self.iterations_before_refresh = 1
        else:
            self.iterations_before_refresh = int(iterations_before_refresh)
        self._counter = 0

    def idle_loop(self):
        if self.in_foreground:
            if self._counter == self.iterations_before_refresh:
                self._counter = 0
            if self._counter == 0:
                self.refresh()
            self._counter += 1
        sleep(self.sleep_time)

    @internal_callback_in_background
    def change_interval(self):
        """
        A helper function to adjust the Refresher's refresh interval while it's running
        """
        new_interval = IntegerAdjustInput(self.refresh_interval, self.i, self.o, message="Refresh interval:").activate()
        if new_interval is not None:
            self.set_refresh_interval(new_interval)

    def set_keymap(self, keymap):
        keymap.update(self.custom_keymap)
        BaseUIElement.set_keymap(self, keymap)

    def generate_keymap(self):
        return {}

    def process_callback(self, func):
        """
        Decorates a function so that during its execution the UI element stops
        being in foreground. Is typically used as a wrapper for a callback from
        input event processing thread. After callback's execution is finished,
        sets the keymap again and refreshes the UI element.
        """
        # This function is copied from base_ui.py - the only difference is
        # the RefresherExitException handling. TODO: think of a prettier way
        # to make it work.
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.to_background()
            self.to_background()
            e = None
            try:
                func(*args, **kwargs)
            except RefresherExitException:
                self.deactivate()
            except Exception as e:
                print_exc()
            logger.debug("{}: executed wrapped function: {}".format(self.name, func.__name__))
            if self.in_background:
                self.to_foreground()
            if e:
                raise e
        return wrapper

    @to_be_foreground
    def refresh(self):
        logger.debug("{}: refreshed data on display".format(self.name))
        try:
            data_to_display = self.refresh_function()
        except RefresherExitException:
            logger.info("{}: received exit exception, deactivating".format(self.name))
            self.deactivate()
            return
        if isinstance(data_to_display, basestring):
            #Passed a string, not a list.
            #Let's be user-friendly and wrap it in a list!
            data_to_display = [data_to_display]
        elif isinstance(data_to_display, tuple):
            #Passed a tuple. Let's convert it into a list!
            data_to_display = list(data_to_display)
        elif isinstance(data_to_display, PIL.Image.Image):
            if "b&w" not in self.o.type:
                raise ValueError("The screen doesn't support showing images!")
            self.o.display_image(data_to_display)
            return
        elif not isinstance(data_to_display, list):
            raise ValueError("refresh_function returned an unsupported type: {}!".format(type(data_to_display)))
        self.o.display_data(*data_to_display)


class RefresherView(object):
    def __init__(self, text_callback, monochrome_callback, color_callback=None):
        self.text_callback = text_callback
        self.monochrome_callback = monochrome_callback
        self.color_callback = color_callback

    def init(self, o):
        if "color" in o.type:
            self.callback = self.color_callback if self.color_callback else self.monochrome_callback
        elif "b&w" in o.type:
            self.callback = self.monochrome_callback
        else:
            self.callback = self.text_callback

    def __call__(self, *args, **kwargs):
        return self.callback(*args, **kwargs)
