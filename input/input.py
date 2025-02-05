from threading import Thread, Event
from traceback import format_exc
from time import sleep
from copy import copy
import importlib
import inspect
import atexit
try:
    from queue import Queue, Empty
except ModuleNotFoundError:
    from Queue import Queue
    Empty = Queue.Empty

from actions import Action
from helpers import setup_logger, KEY_RELEASED, KEY_HELD, KEY_PRESSED

try:
    from input.hotplug import DeviceManager
except ImportError:
    from hotplug import DeviceManager

logger = setup_logger(__name__, "warning")

class CallbackException(Exception):
    def __init__(self, errno=0, message=""):
        self.errno = errno
        self.message = message


class InputProcessor(object):
    """A class which listens for input device events and processes the callbacks
    set in the InputProxy instance for the currently active context."""
    stop_flag = None
    thread_index = 0
    backlight_cb = None

    current_proxy = None
    proxy_methods = ["listen", "stop_listen"]
    proxy_attrs = ["available_keys"]
    proxies = []

    def __init__(self, init_drivers, context_manager):
        self.global_keymap = {}
        self.cm = context_manager
        self.queue = Queue()
        self.available_keys = {}
        self.drivers = {}
        self.initial_drivers = {}
        for driver in init_drivers:
            name = self.attach_driver(driver)
            self.initial_drivers[name] = driver
        atexit.register(self.atexit)

    def receive_key(self, key):
        """
        Receives keypresses from drivers and puts them into ``self.queue``
        for ``self.event_loop`` to process.
        """
        try:
            self.queue.put(key)
        except:
            raise #Just collecting possible exceptions for now

    def attach_driver(self, driver):
        """
        Attaches the driver to ``InputProcessor``.
        """
        # Generating an unique yet human-readable name
        counter = 0
        driver_name = driver.__module__.rsplit('.', 1)[-1]
        name = "{}-{}".format(driver_name, counter)
        while name in self.drivers:
            counter += 1
            name = "{}-{}".format(driver_name, counter)
        logger.info("Attaching driver: {}".format(name))
        self.drivers[name] = driver
        driver._old_send_key = driver.send_key
        # Overriding the send_key method so that keycodes get sent to InputListener
        driver.send_key = self.receive_key
        self.available_keys[name] = driver.available_keys
        self.update_all_proxy_attrs()
        driver.start()
        return name

    def detach_driver(self, name):
        """
        Detaches a driver from the ``InputProcessor``.
        """
        logger.info("Detaching driver: {}".format(name))
        if name in self.initial_drivers.values():
            raise ValueError("Driver {} is from config.json, not removing for safety purposes".format(name))
        driver = self.drivers.pop(name)
        driver.send_key = driver._old_send_key
        driver.stop()
        self.available_keys.pop(name)
        self.update_all_proxy_attrs()

    def list_drivers(self):
        """
        Returns a list of drivers description lists, containing items as follows:

          * Driver name (auto-generated, in form of "driver_name-number")
          * Driver object
          * Available keys
          * ``True`` if driver is supplied from ``config.json``, else ``False``
        """
        return [[name, driver, self.available_keys[name], driver in self.initial_drivers.values()]
                  for name, driver in self.drivers.items()]

    def attach_new_proxy(self, proxy):
        """
        Calls ``detach_proxy``, then ``attach_proxy`` - just a convenience wrapper.
        """
        self.detach_current_proxy()
        self.attach_proxy(proxy)

    def attach_proxy(self, proxy):
        """
        This method is to be called from the ``ContextManager``. Saves a proxy
        internally, so that when a callback is received, its keymap can be
        referenced.
        """
        if self.current_proxy:
            raise ValueError("A proxy is already attached!")
        logger.info("Attaching proxy for context: {}".format(proxy.context_alias))
        self.current_proxy = proxy

    def detach_current_proxy(self):
        """
        This method is to be called from the ContextManager. Saves a proxy
        internally, so that when a callback is received, its keymap can be
        referenced.
        """
        if self.current_proxy:
            logger.info("Detaching proxy for context: {}".format(self.current_proxy.context_alias))
            self.current_proxy = None

    def get_current_proxy(self):
        return self.current_proxy

    def set_global_callback(self, key, callback):
        """
        Sets a global callback for a key. That global callback will be processed
        before the backlight callback or any proxy callbacks.
        """
        logger.info("Setting a global callback for key {}".format(key))
        if key in self.global_keymap.keys():
            #Key is already used in the global keymap
            raise CallbackException(4, "Global callback for {} can't be set because it's already in the keymap!".format(key_name))
        self.global_keymap[key] = callback

    def receive_key(self, key, state = None):
        """
        This is the method that receives keypresses from drivers and puts
        them into ``self.queue``, to be processed by ``self.event_loop``
        Will block with full queue until the queue has a free spot.
        """
        if state is not None:
            self.queue.put((key, state))
        else:
            self.queue.put(key)

    def event_loop(self, index):
        """
        Blocking event loop which just calls ``process_key`` once a key
        is received in the ``self.queue``. Also has some mechanisms that
        make sure the existing event_loop will exit once flag is set, even
        if other event_loop has already started (thought an event_loop can't
        exit if it's still processing a callback.)
        """
        logger.debug("Starting event loop "+str(index))
        self.stop_flag = Event()
        stop_flag = self.stop_flag # Saving a reference.
        # stop_flag is an object that will signal the current input thread to exit or not exit once it's done processing a callback.
        # It'll be called just before self.stop_flag will be overwritten. However, we've got a reference to it and now can check the exact flag this thread itself constructed.
        # Praise the holy garbage collector.
        stop_flag.clear()
        while not stop_flag.isSet():
            if self.get_current_proxy() is not None:
                try:
                    data = self.queue.get(False, 0.1)
                except Empty:
                    # here an active event_loop spends most of the time
                    sleep(0.1)
                except AttributeError:
                    # typically happens upon program termination
                    pass
                else:
                    # here event_loop is usually busy
                    self.process_key(data)
            else:
                # No current proxy set yet, not processing anything
                sleep(0.1)
        logger.debug("Stopping event loop "+str(index))

    def global_key_processed_by_proxy(self, key, state, global_cb):
        """
        Checks whether the global callback execution should be skipped in favor
        of a proxy callback. For example, globally, pressing the green ("ANSWER")
        button should switch you into the "make a call" menu, in other words,
        switch context into the Phone app. However, once you're there, that key should
        not cause a context switch yet again, but instead trigger the "call the
        entered number" action from the proxy keymap!

        At the moment, this mechanism does involve setting non-maskable callbacks
        in the proxy, though.
        """
        current_proxy = self.get_current_proxy()
        # Key force-processed globally
        if isinstance(global_cb, Action):
            if getattr(global_cb, "force_global_key_processing", False):
                return False
        # No proxy set at the moment, weird but OK
        if not current_proxy:
            return False
        if key in current_proxy.nonmaskable_keymap:
            return True

    def process_key(self, data):
        """
        This function receives a keyname, finds the corresponding callback/action
        and handles it. The lookup order is as follows:

            * Global callbacks - set on the InputProcessor itself
            * Proxy non-maskable callbacks
            * Backlight callback (doesn't do anything with the keyname, but dismisses the keypress if it turned on the backlight)
            * Proxy simple callbacks
            * Proxy maskable callbacks
            * Streaming callback (if set, just sends the key to it)

        As soon as a match is found, processes the associated callback and returns.
        """
        if isinstance(data, (tuple, list)) and len(data) == 2:
            key, state = data
            logger.debug("Received key: {}, state: {}".format(key, state))
        elif isinstance(data, basestring):
            key = data
            state = None
            logger.debug("Received key: {}".format(key))
        else:
            raise ValueError("Received unsupported object in place of a key/key+state: {}".format(data))
        # Global and nonmaskable callbacks are supposed to work
        # even when the screen backlight is off
        #
        # First, checking whether the global callbacks apply.
        if key in self.global_keymap:
            global_cb = self.global_keymap[key]
            if not self.global_key_processed_by_proxy(key, state, global_cb):
                self.handle_callback(global_cb, key, state, type="global")
            return
        # Now, all the callbacks are either proxy callbacks or backlight-related
        # Saving a reference to current_proxy, in case it changes during the lookup
        current_proxy = self.get_current_proxy()
        if current_proxy and key in current_proxy.nonmaskable_keymap:
            callback = current_proxy.nonmaskable_keymap[key]
            self.handle_callback(callback, key, state, type="nonmaskable", context_name=current_proxy.context_alias)
            return
        # Checking backlight state, turning it on if necessary
        if callable(self.backlight_cb):
            try:
                # backlight_cb turns on the backlight as an (expected) side effect
                backlight_was_off = self.backlight_cb()
            except:
                logger.exception("Exception while calling the backlight check callback!")
            else:
                # If backlight was off, ignore the keypress
                if backlight_was_off is True:
                    return
        # Now, all the other callbacks of the proxy:
        # Simple callbacks
        if current_proxy and key in current_proxy.keymap:
            callback = current_proxy.keymap[key]
            self.handle_callback(callback, key, state, context_name=current_proxy.context_alias)
        #Maskable callbacks
        elif current_proxy and key in current_proxy.maskable_keymap:
            callback = current_proxy.maskable_keymap[key]
            self.handle_callback(callback, key, state, type="maskable", context_name=current_proxy.context_alias)
        #Keycode streaming
        elif current_proxy and callable(current_proxy.streaming):
            self.handle_callback(current_proxy.streaming, key, state, pass_key=True, type="streaming", context_name=current_proxy.context_alias)
        else:
            logger.debug("Key {} has no handlers - ignored!".format(key))
            pass #No handler for the key

    def handle_callback(self, callback, key, state, pass_key=False, type="simple", context_name=None):
        try:
            if context_name:
                logger.info("Processing a {} callback for key {} with state {}, context {}".format(type, key, state, context_name))
            else:
                logger.info("Processing a {} callback for key {}".format(type, key))
            logger.debug("pass_key = {}".format(pass_key))
            logger.debug("callback name: {}".format(callback.__name__))
            # Checking whether the callback wants key state
            if isinstance(callback, Action):
                callback = callback.cb
            keystate_cb_name = "zpui_icb_pass_key_state"
            if hasattr(callback, "__func__"):
                cb_needs_state = getattr(callback.__func__, keystate_cb_name, False)
            else:
                cb_needs_state = getattr(callback, keystate_cb_name, False)
            # 4 calling conventions - need to pick the right one
            if cb_needs_state is True:
                if pass_key:
                    callback(key, state)
                else:
                    callback(state)
            else:
                # We might also get None for a state if an input driver doesn't support states
                if state == KEY_PRESSED or state is None:
                    if pass_key:
                        callback(key)
                    else:
                        callback()
                else:
                    pass # Not calling the callback if the key is held or released
        except Exception as e:
            locals = inspect.trace()[-1][0].f_locals
            context_alias = getattr(self.get_current_proxy(), "context_alias", None)
            logger.error("Exception {} caused by callback {} when key {}  with state {} was received, context: {}".format(e.__str__() or e.__class__, callback, key, state, context_alias))
            logger.error(format_exc())
            logger.error("Locals of the callback:")
            logger.error(locals)
        finally:
            return

    def listen(self):
        """Start event_loop in a thread. Nonblocking."""
        self.processor_thread = Thread(target = self.event_loop, name="InputThread-"+str(self.thread_index), args=(self.thread_index, ))
        self.thread_index += 1
        self.processor_thread.daemon = True
        self.processor_thread.start()

    def stop_listen(self):
        """This sets a flag for ``event_loop`` to stop. If the ``event_loop()`` is
        currently executing a callback, it will exit as soon as the callback will
        finish executing."""
        if self.stop_flag is not None:
            self.stop_flag.set()

    def atexit(self):
        """Exits driver (if necessary) if something wrong happened or ZPUI exits. Also, stops the InputProcessor, and all the associated drivers."""
        self.stop_listen()
        for driver in self.drivers.values():
            driver.stop()
            if hasattr(driver, "atexit"):
                driver.atexit()
        try:
            self.processor_thread.join()
        except AttributeError:
            pass

    def proxy_method(self, method_name, context_alias, *args, **kwargs):
        if context_alias == self.cm.get_current_context():
            logger.debug("Calling method \"{}\" for proxy \"{}\"".format(method_name, context_alias))
            getattr(self, method_name)(*args, **kwargs)
        else:
            logger.debug("Not calling method \"{}\" for proxy \"{}\" since it's not current".format(method_name, context_alias))
            pass #Ignoring method calls from non-current proxies for now

    def register_proxy(self, proxy):
        context_alias = proxy.context_alias
        self.proxies.append(proxy)
        self.set_proxy_methods(proxy, context_alias)
        self.set_proxy_attrs(proxy)

    def set_proxy_methods(self, proxy, alias):
        for method_name in self.proxy_methods:
            setattr(proxy, method_name, lambda x=method_name, y=alias, *a, **k: self.proxy_method(x, y, *a, **k))

    def set_proxy_attrs(self, proxy):
        for attr_name in self.proxy_attrs:
            setattr(proxy, attr_name, copy(getattr(self, attr_name)))

    def update_all_proxy_attrs(self):
        """
        Updates all the proxied attributes for proxies, to be triggered when
        one of the attributes is changed.
        """
        for proxy in self.proxies:
            self.set_proxy_attrs(proxy)


class InputProxy(object):
    reserved_keys = ["KEY_LEFT", "KEY_RIGHT", "KEY_UP", "KEY_DOWN", "KEY_ENTER"]
    deprecated_keys = ["KEY_PAGEUP", "KEY_PAGEDOWN"]

    def __init__(self, context_alias):
        self.keymap = {}
        self.streaming = None
        self.maskable_keymap = {}
        self.nonmaskable_keymap = {}
        self.context_alias = context_alias

    def set_streaming(self, callback):
        """
        Sets a callback for streaming key events. This callback will be called
        each time a key is pressed that doesn't belong to one of the three keymaps.

        The callback will be called  with key_name as first argument but should
        support arbitrary number of keyword arguments if compatibility with
        future versions is desired. (basically, add ``**kwargs`` to it).

        If a callback was set before, replaces it. The callbacks set will not be
        restored after being replaced by other callbacks. Care must be taken to
        make sure that the callback is only executed when the app or UI element
        that set it is active.
        """
        self.streaming = callback

    def remove_streaming(self):
        """
        Removes a callback for streaming key events, if previously set by any
        app/UI element. This is more of a convenience function, to avoid your
        callback being called when your app or UI element is not active.
        """
        self.streaming = None

    def set_callback(self, key_name, callback, silent=False):
        """
        Sets a single callback. The ``silent`` kwarg can be set so that the callback is not sanity checked (warnings shown in the logs).

        >>> i = InputProxy("test")
        >>> i.clear_keymap()
        >>> i.set_callback("KEY_ENTER", lambda: None)
        >>> "KEY_ENTER" in i.keymap
        True
        """
        if not silent:
            self.sanity_check_cb(key_name, callback)
        self.keymap[key_name] = callback

    def sanity_check_cb(self, key_name, callback):
        """ Checks the keyname and callback. Can be turned off by ``silent=True`` passed to ``set_keymap``/``set_callback``/etc. """
        if not callable(callback):
            logger.warning("Proxy {} - supplied callback for key {} is not callable - is {}".format(self.context_alias, key_name, callback))
        if key_name in self.deprecated_keys:
            logger.warning("Proxy {} - key {} is deprecated in ZPUI, use with caution.".format(self.context_alias, key_name))

    def check_special_callback(self, key_name):
        """Raises exceptions upon setting of a special callback on a reserved/taken keyname."""
        if key_name in self.reserved_keys:
            #Trying to set a special callback for a reserved key
            raise CallbackException(1, "Special callback for {} can't be set because it's one of the reserved keys".format(key_name))
        if key_name in self.nonmaskable_keymap:
            #Key is already used in a non-maskable callback
            raise CallbackException(2, "Special callback for {} can't be set because it's already set as nonmaskable".format(key_name))
        elif key_name in self.maskable_keymap:
            #Key is already used in a maskable callback
            raise CallbackException(3, "Special callback for {} can't be set because it's already set as maskable".format(key_name))

    def set_maskable_callback(self, key_name, callback, silent=False):
        """Sets a single maskable callback. Raises ``CallbackException``
        if the callback is one of the reserved keys or already is in maskable/nonmaskable
        keymap.

        A maskable callback is global (can be cleared) and will be called upon a keypress
        unless a callback for the same keyname is already set in ``keymap``."""
        self.check_special_callback(key_name)
        if not silent:
            self.sanity_check_cb(key_name, callback)
        self.maskable_keymap[key_name] = callback

    def set_nonmaskable_callback(self, key_name, callback, silent=False):
        """Sets a single nonmaskable callback. Raises ``CallbackException``
        if the callback is one of the reserved keys or already is in maskable/nonmaskable
        keymap. The ``silent`` kwarg can be set so that the callback is not sanity checked (warnings shown in the logs).

        A nonmaskable callback is global (never cleared) and will be called upon a keypress
        even if a callback for the same keyname is already set in ``keymap``
        (callback from the ``keymap`` won't be called)."""
        self.check_special_callback(key_name)
        if not silent:
            self.sanity_check_cb(key_name, callback)
        self.nonmaskable_keymap[key_name] = callback

    def remove_callback(self, key_name):
        """Removes a single callback."""
        self.keymap.pop(key_name)

    def remove_maskable_callback(self, key_name):
        """Removes a single maskable callback."""
        self.maskable_keymap.pop(key_name)

    def get_keymap(self):
        """Returns the current keymap."""
        return self.keymap

    def set_keymap(self, new_keymap, silent=False):
        """
        Sets all the callbacks supplied, removing the previously set keymap completely.
        The ``silent`` kwarg can be set so that the callback is not sanity checked (warnings shown in the logs).
        """
        if not silent:
            for key_name, callback in new_keymap.items():
                self.sanity_check_cb(key_name, callback)
        self.keymap = new_keymap

    def update_keymap(self, new_keymap, silent=False):
        """
        Updates the InputProxy keymap with entries from another keymap.
        Will add/replace callbacks for keys in the new keymap,
        but will leave the existing keys that are not in new keymap intact.
        The ``silent`` kwarg can be set so that the callback is not sanity checked
        (warnings shown in the logs).

        >>> i = InputProxy("test")
        >>> i.set_keymap({"KEY_LEFT":lambda:1, "KEY_DOWN":lambda:2})
        >>> i.keymap["KEY_LEFT"]()
        1
        >>> i.keymap["KEY_DOWN"]()
        2
        >>> i.update_keymap({"KEY_LEFT":lambda:3, "KEY_1":lambda:4})
        >>> i.keymap["KEY_LEFT"]()
        3
        >>> i.keymap["KEY_DOWN"]()
        2
        >>> i.keymap["KEY_1"]()
        4
        """
        keymap_replacement = {}
        keymap_replacement.update(self.keymap)
        keymap_replacement.update(new_keymap)
        self.set_keymap(keymap_replacement, silent=silent)

    def clear_keymap(self):
        """Removes all the callbacks set."""
        self.keymap = {}


def init(driver_configs, context_manager):
    """ This function is called by main.py to read the input configuration,
    pick the corresponding drivers and initialize InputProcessor. Returns
    the InputProcessor instance created.`"""
    drivers = []
    for driver_config in driver_configs:
        driver_name = driver_config["driver"]
        driver_module = importlib.import_module("input.drivers."+driver_name)
        args = driver_config.get("args", [])
        kwargs = driver_config.get("kwargs", {})
        driver = driver_module.InputDevice(*args, **kwargs)
        drivers.append(driver)
    i = InputProcessor(drivers, context_manager)
    dm = DeviceManager(i)
    return i, dm

if __name__ == "__main__":
    import doctest
    doctest.testmod()
