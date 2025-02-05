import os
from time import sleep
from functools import wraps
from threading import Event
from traceback import print_exc
from inspect import getframeinfo, stack

import PIL

from helpers import setup_logger
from ui.utils import to_be_foreground

logger = setup_logger(__name__, "info")

def internal_callback_in_background(method):
    """
      A decorator for UI elements' internal methods that need to bring the UI element
      into the background during execution.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        self.to_background()
        method(self, *args, **kwargs)
        logger.debug("{}: executed wrapped function: {}".format(self.name, method.__name__))
        if self.in_background:
            self.to_foreground()
    return wrapper


class BaseUIElement(object):

    def __init__(self, i, o, name=None, override_left=True, input_necessary=True):
        """
        Sets the most basic variables and checks whether the input object
        is supplied in case it's necessary. To be called by a child object.
        """
        self.i = i
        self.o = o
        if name is not None:
            self.name = name
        else:
            self.generate_name_if_not_supplied()
        self.overlays = []
        self._in_foreground = Event()
        self._in_background = Event()
        self._input_necessary = input_necessary
        self._override_left = override_left
        if not i and input_necessary:
            raise ValueError("UI element {} needs an input object supplied!".format(self.name))
        self.check_properties()
        self.set_default_keymap()

    def check_properties(self):
        properties = ["in_foreground", "in_background", "is_active"]
        for p in properties:
            assert isinstance(getattr(self, p), bool), "{} needs to be a property".format(p)

    @property
    def in_foreground(self):
        return self._in_foreground.isSet()

    @in_foreground.setter
    def in_foreground(self, value):
        self._in_foreground.set() if value else self._in_foreground.clear()

    @property
    def in_background(self):
        return self._in_background.isSet()

    @in_background.setter
    def in_background(self, value):
        self._in_background.set() if value else self._in_background.clear()

    def to_foreground(self):
        """
        A method that is called once in ``activate`` to set all the variables,
        activates the input device and draw the first image on the display.
        """
        logger.debug("{} in foreground".format(self.name))
        self.before_foreground()
        self.in_background = True
        self.in_foreground = True
        self.activate_input()
        self.refresh()

    def to_background(self):
        """ Signals ``activate`` to finish executing. """
        self.in_foreground = False
        logger.debug("{} in background".format(self.name))

    def before_foreground(self):
        """Hook for child UI elements. Is called each time to_foreground is called."""
        pass

    def before_activate(self):
        """
        Hook for child UI elements, is called each time activate() is called.
        Is the perfect place to clear any flags that you don't want to persist
        between multiple activations of a single instance of an UI element.
        """
        pass

    def after_activate(self):
        """
        Hook for child UI elements, is called each time before activate() returns -
        before ``get_return_value`` is called. Is the perfect place to, say, remove
        input streaming callbacks.
        """
        pass

    def activate(self):
        """
        A method which is called when the UI element needs to start operating.
        Is blocking, sets up input&output devices, refreshes the UI element,
        then calls the ``idle_loop`` method while the UI element is active.
        ``self.in_foreground`` is True, while callbacks are executed from the
        input device thread.
        """
        self.before_activate()
        logger.debug("{} activated".format(self.name))
        self.to_foreground()
        while self.is_active:
            self.idle_loop()
        self.after_activate()
        return_value = self.get_return_value()
        logger.debug("{} exited".format(self.name))
        return return_value

    def get_return_value(self):
        """
        Can be overridden by child UI elements. Return value will be returned when
        UI element's ``activate()`` exits.
        """
        return None  # Default value to indicate that no meaningful result was returned

    @property
    def is_active(self):
        """
        A condition to be checked by ``activate`` to see when the UI element
        is active. Can be overridden by child elements if necessary.
        By default returns ``self.in_background``, so if you only have a
        single UI element without external callback processing, it might make
        sense to check ``in_foreground`` instead.
        """
        return self.in_background

    def idle_loop(self):
        """
        A method that will be called all the time while the UI element is in background
        (regardless of whether it's in foreground or not).
        To be implemented by a child object.
        """
        raise NotImplementedError

    def deactivate(self):
        """ Deactivates the UI element, exiting it. """
        self.in_foreground = False
        self.in_background = False
        logger.debug("{} deactivated".format(self.name))

    def print_name(self):
        """ A debug method. Useful for hooking up to an input event so that
        you can see which UI element is currently active. """
        logger.debug("{} is currently active".format(self.name))

    def print_keymap(self):
        """ A debug method. Useful for hooking up to an input event so that
        you can see what's the keymap of a currently active UI element. """
        logger.debug("{} has keymap: {}".format(self.name, self.keymap))

    def process_callback(self, func):
        """
        Decorates a function so that during its execution the UI element stops
        being in foreground. Is typically used as a wrapper for a callback from
        input event processing thread. After callback's execution is finished,
        sets the keymap again and refreshes the UI element.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.to_background()
            e = None
            try:
                func(*args, **kwargs)
            except Exception as e:
                print_exc()
            logger.debug("{}: executed wrapped function: {}".format(self.name, func.__name__))
            if self.in_background:
                self.to_foreground()
            if e:
                raise e
        return wrapper

    def process_keymap(self, keymap):
        """
        Processes the keymap, wrapping all callbacks using the ``process_callback`` method.
        If a string is supplied instead of a callable, it looks it up from methods -
        if a method is not found, raises ``ValueError``.
        Also, sets KEY_LEFT to ``deactivate`` unless ``self.override_left``
        is set to ``False`` (override with caution).
        """
        logger.debug("{}: processing keymap - {}".format(self.name, keymap))
        for key in keymap:
            callback_or_name = keymap[key]
            if isinstance(callback_or_name, basestring):
                if hasattr(self, callback_or_name):
                    callback = getattr(self, callback_or_name)
                    keymap[key] = callback
                else:
                    raise ValueError("{}: {} not an attribute/method or callable".format(self.name, callback_or_name))
            elif callable(callback_or_name):
                callback = self.process_callback(keymap[key])
                keymap[key] = callback
            else:
                raise ValueError("{}: {} is not a callable".format(self.name, callback_or_name))
        if self._override_left:
            if not "KEY_LEFT" in keymap:
                keymap["KEY_LEFT"] = self.deactivate
        return keymap

    def set_keymap(self, keymap):
        """
        Receives and processes UI element's keymap (filtered using ``process_keymap``
        before setting).
        """
        self.keymap = self.process_keymap(keymap)

    def set_default_keymap(self):
        """
        Sets the default keymap, getting it straight from the ``generate_keymap``.
        """
        self.set_keymap(self.generate_keymap())

    def generate_keymap(self):
        """
        Returns the default keymap for the UI element.
        To be implemented by a child object.
        """
        raise NotImplementedError

    def update_keymap(self, new_keymap):
        """
        Updates the UI element's keymap with a new one (filtered using
        ``process_keymap`` before updating).
        """
        self._override_left = False
        processed_keymap = self.process_keymap(new_keymap)
        self._override_left = True
        self.keymap.update(processed_keymap)

    def configure_input(self):
        """
        Configures the input device - you can set your keymap, streaming callbacks
        or both - abstracting away ``stop_listen`` and ``listen``. Can be overridden
        by child elements.
        """
        self.i.clear_keymap()
        self.i.set_keymap(self.keymap)

    @to_be_foreground
    def activate_input(self):
        """
        Sets up the input device if one was passed to the UI element - calling
        ``i.stop_listen``, ``self.configure_input`` and ``i.listen``. If an input
        element wasn't passed, checks if one is expected.
        """
        if self.i:
            self.i.stop_listen()
            self.configure_input()
            self.i.listen()
        else:
            if self._input_necessary:
                raise ValueError("UI element {} needs an input object supplied!")
            else:
                logger.warning("{}: no input device object supplied, not setting the keymap".format(self.name))

    @to_be_foreground
    def refresh(self):
        """
        Is called when the screen contents have to be updated.
        To be implemented by a child object.
        """
        raise NotImplementedError

    def generate_name_if_not_supplied(self):
        """ Generating a random yet descriptive UI element name if one was not supplied.
        The name hasa to be random enough so that overlays can be applied properly.
        The name generated will include the directory where the app is called from."""
        cwd = os.getcwd()
        st = stack()
        last_filename = None
        filename = None
        lineno = None
        for i, frame in enumerate(st):
            caller = getframeinfo(frame[0])
            filename = caller.filename
            lineno = caller.lineno
            if filename.startswith(cwd):
                filename = filename[len(cwd):].lstrip("/")
            if filename.startswith("apps/"):
                # First frame that starts with 'apps' - likely is a frame from the app file
                break
            elif not filename.startswith('ui') and last_filename and last_filename.startswith('ui'):
                # First frame that does not start with 'ui' - likely is a useful frame
                break
            last_filename = filename
        else:
            # No suitable frame found? 0_0
            logger.warning("No suitable frame found for UI element {} at {} while generating a name, overlays might not apply correctly!".format(self.__class__.__name__, id(self)))
        self.name = "{} from {}:{}".format(self.__class__.__name__, filename, lineno)
        logger.warning("No name supplied for an UI element {} at {}, generated a new name: {}".format(self.__class__.__name__, id(self), repr(self.name)))
