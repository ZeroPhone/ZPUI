from input.input import InputProxy
from output.output import OutputProxy
from actions import ContextSwitchAction
from action_manager import ActionManager

from functools import wraps
from threading import Thread, Lock

from helpers import setup_logger

logger = setup_logger(__name__, "info")

def context_target_wrapper(context, func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            raise
        finally:
            logger.info("Context {} finished, signalling".format(context.name))
            context.signal_finished()
    return wrapper


class ContextError(Exception):
    pass


class Context(object):
    thread = None
    target = None
    threaded = True
    i = None
    o = None
    menu_name = None

    def __init__(self, name, event_callback):
        self.name = name
        self.event_cb = event_callback

    def set_target(self, target):
        """
        Sets a function to be called once context is switched. This way,
        you can define a custom callback to be used for your app.
        """
        self.target = target

    def set_io(self, i, o):
        """
        Saves references to proxy IO objects in the context object
        (this function is used by the context manager)
        """
        self.i = i
        self.o = o

    def get_io(self):
        """
        Returns proxy IO objects used by the app that the context belongs to.
        """
        return self.i, self.o

    def activate(self, start_thread=True):
        """
        Starts the context - if it's threaded, starts the thread, otherwise it assumes
        that there's already a running thread and does nothing. In latter case, throws
        an exception if it detects that a supposedly non-threaded context has the ``threaded``
        flag set.
        """
        if self.is_threaded() and start_thread:
            if not self.thread_is_active():
                self.verify_target()
                self.start_thread()
            else:
                logger.debug("A thread for the {} context seems to already be active, not doing anything".format(self.name))
        else:
            if self.name == "main":
                logger.debug("Main context does not have thread target, that is to be expected")
            elif not start_thread:
                logger.info("Instructed not to start the thread for context {}".format(self.name))
            elif self.threaded:
                logger.warning("Context {} does not have a target! Raising an exception".format(self.name))
                raise ContextError("Context {} does not have a target!".format(self.name))

    def verify_target(self):
        """
        Checks whether a valid target is set - at the very least, a callable.
        """
        if not callable(self.target):
            raise ContextError("Context {} expected callable target, got {}!".format(self.name, type(self.target)))

    def is_threaded(self):
        """
        Tells whether the context is threaded or not - checking whether target exists and
        ``threaded`` flag is set.
        """
        return self.threaded and self.target is not None

    def thread_is_active(self):
        """
        Tells whether there's a currently-running thread associated with the context.
        """
        return self.thread and self.thread.isAlive()

    def start_thread(self):
        """
        Actually launches the context thread (based on the target function,
        wrapped into the ``context_target_wrapper()``.
        """
        wrapped_target = context_target_wrapper(self, self.target)
        if self.thread: del self.thread
        self.thread = Thread(target=wrapped_target, name="Thread for context {} (target: {})".format(self.name, self.target.__name__))
        self.thread.daemon = True
        self.thread.start()

    def signal_finished(self):
        """
        Signals to the ContextManager that the application has finished running,
        as well as clears the display (to avoid a bug from happening, where last
        contents of the display are shortly shown on the next reactivation).
        """
        self.o._clear()
        return self.event_cb(self.name, "finished")

    def signal_background(self):
        """
        Signals to the ContextManager that the application wants to go into background.
        Currently, has the same effect as ``signal_finished`` - except it doesn't
        clear the screen.
        """
        return self.event_cb(self.name, "background")

    def list_contexts(self):
        """
        Returns a list of all available contexts, containing:

        * Name (``"name"``) of the context
        * Menu name (``"menu_name"``) of the associated menu entry (if one exists, else ``None``)
        * Previous context name (``"previous_context"``) for the context (if one exists, else ``None``)
        * Status (``"state"``) - ``"inactive"``, ``"running"`` or ``"non-threaded"``
        """
        return self.event_cb(self.name, "list_contexts")

    def request_exclusive(self):
        """
        Request exclusive context switch for an app. You can't switch away from it until
        the switch is rescinded.
        """
        return self.event_cb(self.name, "request_exclusive")

    def rescind_exclusive(self):
        """
        Rescind exclusive context switch from the app. Will only work if such a context is
        already requested.
        """
        return self.event_cb(self.name, "rescind_exclusive")

    def exclusive_status(self):
        """
        Request whether there's an app that has grabbed exclusive context.
        """
        return self.event_cb(self.name, "exclusive_status")

    def request_switch(self, requested_context=None, start_thread=True):
        """
        Requests ContextManager to switch to the context in question. If switch is done,
        returns True, otherwise returns False. If a context name is supplied,
        will switch to that context.
        """
        if requested_context:
            return self.event_cb(self.name, "request_switch_to", requested_context, start_thread=start_thread)
        else:
            return self.event_cb(self.name, "request_switch", start_thread=start_thread)

    def request_context_start(self, context_alias):
        """
        Asks ContextManager to start a context in the background.
        Useful for i.e. a lockscreen starting an app that it'll grab images
        from so that they can be displayed on the lockscreen's idle screen.
        """
        return self.event_cb(self.name, "request_context_start", context_alias)

    def is_active(self):
        """
        Tells whether this context is the one active.
        """
        return self.event_cb(self.name, "is_active")

    def get_previous_context_image(self):
        """
        Useful for making screenshots (mainly, for ZeroMenu). Might get deprecated in
        the future, once a better way to do this is found.
        """
        return self.event_cb(self.name, "get_previous_context_image")

    def get_context_image(self, context_alias):
        """
        Useful for showing images from other contexts - i.e. lockscreen.
        """
        return self.event_cb(self.name, "get_context_image", context_alias)

    def register_action(self, action):
        """
        Allows an app to register an 'action' that can be used by other apps -
        for example, ZeroMenu.
        """
        return self.event_cb(self.name, "register_action", action)

    def register_firstboot_action(self, action):
        """
        Allows an app to register an action that shall be run on ZP first boot.
        """
        return self.event_cb(self.name, "register_firstboot_action", action)

    def get_actions(self):
        return self.event_cb(self.name, "get_actions")

    def request_global_keymap(self, keymap):
        """
        Requests ContextManager to set callbacks into the global keymap.
        Returns a dictionary with results for each set key (with keys as dict. keys):
        if a callback for the key was set successfully, the value is True;
        otherwise, the value will be an exception raised in the process.

        Might get deprecated in the future, once a better way to do this is found.
        """
        return self.event_cb(self.name, "request_global_keymap", keymap)


class ContextManager(object):

    current_context = None
    exclusive_context = None
    fallback_context = "main"
    initial_contexts = ["main"]
    start_context = "main"
    allowed_exclusive_contexts = ["apps.lockscreen", "apps.firstboot_wizard"]

    def __init__(self):
        self.contexts = {}
        self.previous_contexts = {}
        self.switching_contexts = Lock()
        self.am = ActionManager(self)

    def init_io(self, input_processor, screen):
        """
        Saves references to hardware IO objects and creates initial contexts.
        """
        self.input_processor = input_processor
        self.screen = screen
        self.create_initial_contexts()

    def create_initial_contexts(self):
        """
        Creates contexts specified in ``self.initial_contexts`` - since
        targets aren't set, marks them as non-threaded.
        """
        for context_alias in self.initial_contexts:
            c = self.create_context(context_alias)
            c.threaded = False

    def switch_to_start_context(self):
        """
        Switches to the defined start context - usually "main",
        but could also be some other context defined by someone
        integrating ZPUI into their workflow.
        """
        self.unsafe_switch_to_context(self.start_context, do_raise=False)

    def get_context_names(self):
        """
        Gets names of all contexts available.
        """
        return self.contexts.keys()

    def get_current_context(self):
        """
        Returns the alias (name) of the current context.
        """
        return self.current_context

    def register_context_target(self, context_alias, target):
        """
        A context manager-side function that sets the target for a context.
        """
        logger.debug("Registering a thread target for the {} context".format(context_alias))
        self.contexts[context_alias].set_target(target)

    def set_menu_name(self, context_alias, menu_name):
        """
        A context manager-side function that associates a menu name with a context.
        """
        self.contexts[context_alias].menu_name = menu_name

    def switch_to_context(self, context_alias, start_thread=True):
        """
        Lets you switch to another context by its alias.
        """
        # Saving the current context alias in the "previous context" storage
        if context_alias != self.current_context:
            self.previous_contexts[context_alias] = self.current_context
            with self.switching_contexts:
                try:
                    self.unsafe_switch_to_context(context_alias, start_thread=start_thread)
                except ContextError:
                    logger.exception("A ContextError was caught")
                    self.previous_contexts.pop(context_alias)
                    return False
                else:
                    return True

    def unsafe_switch_to_context(self, context_alias, do_raise=True, start_thread=True):
        """
        This is a non-thread-safe context switch function. Not to be used directly
        - is only for internal usage. In case an exception is raised, sets things as they
        were before and re-raises the exception.
        """
        logger.info("Switching to {} context".format(context_alias))
        previous_context = self.current_context
        self.current_context = context_alias
        # First, activating IO - if it fails, restoring the previous context's IO
        try:
            self.activate_context_io(context_alias)
        except:
            logger.exception("Switching to the {} context failed - couldn't activate IO!".format(context_alias))
            try:
                self.activate_context_io(previous_context)
            except:
                logger.exception("Also couldn't activate IO for the previous context: {}!".format(previous_context))
                self.failsafe_switch_to_fallback_context()
                if do_raise:
                    raise
            self.current_context = previous_context
            # Passing the exception back to the caller
            if do_raise:
                raise
        # Activating the context - restoring everything if it fails
        try:
            self.contexts[context_alias].activate(start_thread=start_thread)
        except:
            logger.exception("Switching to the {} context failed - couldn't activate the context!".format(context_alias))
            # Activating IO of the previous context
            try:
                self.activate_context_io(previous_context)
            except:
                logger.exception("Also couldn't activate IO for the previous context: {}!".format(previous_context))
                self.failsafe_switch_to_fallback_context()
                if do_raise:
                    raise
            # Activating the previous context itself
            try:
                self.contexts[previous_context].activate()
            except:
                logger.exception("Also couldn't activate context for the previous context: {}!".format(previous_context))
                self.failsafe_switch_to_fallback_context()
                if do_raise:
                    raise
            self.current_context = previous_context
            # Passing the exception back to the caller
            if do_raise:
                raise
        else:
            logger.debug("Switched to {} context!".format(context_alias))

    def failsafe_switch_to_fallback_context(self):
        """
        Last resort function for the ``unsafe_switch_to_context`` to use
        when both switching to the context and failsafe switching fails.
        """
        logger.warning("Some contexts broke, switching to fallback context: {}".format(self.fallback_context))
        self.current_context = self.fallback_context
        # In case something fucked up in the previous context dictionary, fixing that
        # More like - working around, preventing the user from making more mistakes
        self.previous_contexts[self.fallback_context] = self.fallback_context
        self.activate_context_io(self.current_context)
        self.contexts[self.current_context].activate()
        logger.info("Fallback switched to {} - proceed with caution".format(self.current_context))

    def activate_context_io(self, context_alias):
        """
        This method activates input and output objects associated with a context.
        """
        logger.debug("Activating IO for {} context".format(context_alias))
        proxy_i, proxy_o = self.contexts[context_alias].get_io()
        if not isinstance(proxy_i, InputProxy) or not isinstance(proxy_o, OutputProxy):
            raise ContextError("Non-proxy IO objects for the context {}".format(context_alias))
        self.input_processor.attach_new_proxy(proxy_i)
        self.screen.attach_new_proxy(proxy_o)

    def create_context(self, context_alias):
        """
        Creates a context object (with IO) and saves it internally
        (by the given context alias).
        """
        logger.debug("Creating {} context".format(context_alias))
        context = Context(context_alias, self.signal_event)
        context.set_io(*self.create_io_for_context(context_alias))
        self.contexts[context_alias] = context
        return context

    def create_io_for_context(self, context_alias):
        """
        Creates IO objects for the context, registers them and returns them.
        """
        proxy_i = InputProxy(context_alias)
        proxy_o = OutputProxy(context_alias)
        self.input_processor.register_proxy(proxy_i)
        self.screen.init_proxy(proxy_o)
        self.set_default_callbacks_on_proxy(context_alias, proxy_i)
        return proxy_i, proxy_o

    def set_default_callbacks_on_proxy(self, context_alias, proxy_i):
        """
        Sets some default callbacks on the input proxy. For now, the only
        callback is the KEY_LEFT maskable callback exiting the app -
        in case the app is hanging for some reason.
        """
        flc = lambda x=context_alias: self.failsafe_left_handler(x)
        proxy_i.maskable_keymap["KEY_LEFT"] = flc

    def get_io_for_context(self, context_alias):
        """
        Returns the IO objects for the context.
        """
        return self.contexts[context_alias].get_io()

    def get_previous_context(self, context_alias, pop=False):
        """
        Returns name of the previous context for a given context. If ``pop``
        is set to True, also removes the name from the internal dictionary.
        """
        # WORKAROUND, future self - TODO please reconsider
        # (after you move between different contexts a lot and trigger something,
        # say, use ZeroMenu to switch to main context,
        # pressing LEFT in main context can move you to another context,
        # probably because of context switcing mechanics and previous context stuff.
        if context_alias == self.fallback_context:
            return context_alias
        if pop:
            prev_context = self.previous_contexts.pop(context_alias, self.fallback_context)
        else:
            prev_context = self.previous_contexts.get(context_alias, self.fallback_context)
        # If previous context is, by some chance, the same, let's fall back
        if prev_context == context_alias:
            prev_context = self.fallback_context
        return prev_context

    def failsafe_left_handler(self, context_alias):
        """
        This function is set up as the default maskable callback for new contexts,
        so that users can exit on LEFT press if the context is waiting.
        """
        previous_context = self.get_previous_context(context_alias)
        if not previous_context:
            previous_context = self.fallback_context
        self.switch_to_context(previous_context)

    def signal_event(self, context_alias, event, *args, **kwargs):
        """
        A callback for context objects to use to signal/receive events -
        providing an interface for apps to interact with the context manager.
        This function will, at some point in the future, be working through
        RPC.
        """
        if event == "finished" or event == "background":
            # For now, those two events are handled the same - later on,
            # there will be differences.
            with self.switching_contexts:
                #Locking to avoid a check-then-do race condition
                if self.current_context == context_alias:
                    #Current context is the active one, switching to the previous context
                    next_context = self.get_previous_context(context_alias, pop=True)
                    logger.debug("Next context: {}".format(next_context))
                    try:
                        self.unsafe_switch_to_context(next_context)
                    except ContextError:
                        logger.exception("A ContextError was caught")
                        self.previous_contexts[context_alias] = next_context
                        return False
                    return True
                else:
                    return False
        elif event == "get_previous_context_image":
            # This is a special-case function for screenshots. I'm wondering
            # if there's a better way to express this.
            previous_context = self.get_previous_context(self.current_context)
            return self.contexts[previous_context].get_io()[1].get_current_image()
        elif event == "get_context_image":
            # This is a special-case function for lockscreens. I'm wondering
            # if there's a better way to express this.
            context = args[0]
            return self.contexts[context].get_io()[1].get_current_image()
        elif event == "is_active":
            return context_alias == self.current_context
        elif event == "register_action":
            action = args[0]
            action.full_name = "{}-{}".format(context_alias, action.name)
            action.context = context_alias
            if isinstance(action, ContextSwitchAction) and action.target_context is None:
                action.target_context = context_alias
            self.am.register_action(action)
        elif event == "register_firstboot_action":
            action = args[0]
            self.am.register_firstboot_action(action, context_alias)
        elif event == "request_exclusive":
            if self.exclusive_context and self.exclusive_context != context_alias:
                logger.warning("Context {} requested exclusive switch but {} already got it".format(context_alias, self.exclusive_context))
                return False
            if context_alias in self.allowed_exclusive_contexts:
                logger.warning("Context {} requested exclusive switch, allowing".format(context_alias))
                self.exclusive_context = context_alias
                self.switch_to_context(context_alias)
                return True
            else:
                logger.warning("Context {} requested exclusive switch - not allowed!".format(context_alias))
                return False
        elif event == "rescind_exclusive":
            if self.exclusive_context == context_alias:
                self.exclusive_context = None
                return True
            else:
                return False
        elif event == "exclusive_status":
            return True if self.exclusive_context else False
        elif event ==  "get_actions":
            return self.am.get_actions()
        elif event == "list_contexts":
            logger.info("Context list requested by {} app".format(context_alias))
            c_list = []
            for name in self.contexts:
                c = {}
                context = self.contexts[name]
                c["name"] = name
                c["menu_name"] = context.menu_name
                c["previous_context"] = self.get_previous_context(name)
                if not context.is_threaded():
                    c["state"] = "non-threaded"
                else:
                    c["state"] = "running" if context.thread_is_active() else "inactive"
                c_list.append(c)
            return c_list
        elif event == "request_switch":
            # As usecases appear, we will likely want to do some checks here
            logger.info("Context switch requested by {} app".format(context_alias))
            if self.exclusive_context:
                # If exclusive context is active, only an app that has it
                # can initiate a switch.
                if context_alias != self.exclusive_context:
                    return False
            return self.switch_to_context(context_alias, start_thread=kwargs.get("start_thread", True))
        elif event == "request_switch_to":
            # If app is not the one active, should we honor its request?
            # probably not, but we might want to do something about it
            # to be considered
            if self.exclusive_context:
                # If exclusive context is active, only an app that has it
                # can initiate a switch to other context
                if context_alias != self.exclusive_context:
                    return False
            new_context = args[0]
            logger.info("Context switch to {} requested by {} app".format(new_context, context_alias))
            return self.switch_to_context(new_context, start_thread=kwargs.get("start_thread", True))
        elif event == "request_context_start":
            context_alias = args[0]
            return self.contexts[context_alias].activate()
        elif event == "request_global_keymap":
            results = {}
            keymap = args[0]
            for key, cb in keymap.items():
                try:
                    self.input_processor.set_global_callback(key, cb)
                except Exception as e:
                    logger.warning("Context {} couldn't set a global callback on {} (function: {})".format(context_alias, key, cb.__name__))
                    results[key] = e
                else:
                    logger.warning("Context {} set a global callback on {} (function: {})".format(context_alias, key, cb.__name__))
                    results[key] = True
            return results
        else:
            logger.warning("Unknown event: {}!".format(event))
