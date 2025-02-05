from functools import wraps
from copy import deepcopy
import importlib

# These base classes document functions that
# different output devices are expected to have.

class OutputDevice(object):
    """Common class for all OutputDevices, no matter if they're graphical or character-based."""

    current_proxy = None

    def attach_new_proxy(self, proxy):
        self.detach_current_proxy()
        self.attach_proxy(proxy)

    def detach_current_proxy(self):
        self.current_proxy = None

    def attach_proxy(self, proxy):
        self.current_proxy = proxy
        proxy.on_attach()

    def init_proxy(self, proxy):
        base_classes = self.__base_classes__
        base_classes_items = sum([list(cls.__dict__.items()) for cls in base_classes], [])
        #print(base_classes_items)
        public_attributes = [ (k, v) for (k, v) in base_classes_items if not k.startswith("_") ]
        hidden_attributes = ["current_proxy", "current_image"]
        hidden_methods = ["init_proxy", "proxify_method", "detach_current_proxy", "attach_proxy", "get_proxied_method", "proxify_method"]
        attribute_names = [ k for (k, v) in public_attributes if not callable(v) and k not in hidden_attributes]
        method_names = [ k for (k, v) in public_attributes if callable(v) and k not in hidden_methods]
        direct_methods = ["display_data_onto_image"]

        for attribute_name in attribute_names:
            #print("attribute: {}".format(attribute_name))
            # Setting attributes of the proxy object to the same values
            # as the current output device has them
            value = getattr(self, attribute_name)
            # Making sure that changing the proxy object's attributes
            # won't change the attributes of the original object
            copied_value = deepcopy(value)
            setattr(proxy, attribute_name, copied_value)
            #print("Setting to value {}".format(copied_value))
        for method_name in method_names:
            #print("method: {}".format(method_name))
            # Setting functions to proxy the current object's
            self.proxify_method(proxy, method_name)
        for method_name in direct_methods:
            # Methods that are proxied directly
            setattr(proxy, method_name, getattr(self, method_name))
        # Proxies have no use for hidden methods
        # Unless
        #for attribute_name in hidden_attributes+hidden_methods:
        #    if hasattr(proxy, attribute_name):
        #        delattr(proxy, attribute_name)

    def get_proxied_method(o, proxy, method_name, sideeffect):
        method = getattr(o, method_name)
        @wraps(method)
        def wrapper(*args, **kwargs):
            #print("Method: "+method_name)
            sideeffect(*args, **kwargs)
            #print("Current: "+o.current_proxy.context_alias)
            #print("Called from: "+proxy.context_alias)
            if o.current_proxy.context_alias == proxy.context_alias:
                #print("Calling the method directly!")
                #print(args)
                method(*args, **kwargs)
            else:
                pass #print("Not calling the method directly!")
            #print("")
        return wrapper

    def proxify_method(self, proxy, method_name):
        # If a proxy defines a side effect to happen when the function is called,
        # we call it with same arguments and kwargs as the function received
        # (and we make a small empty lambda if there's no side effect)
        sideeffect = getattr(proxy, "_"+method_name, lambda *a, **k: None)
        proxied_method = self.get_proxied_method(proxy, method_name, sideeffect)
        setattr(proxy, method_name, proxied_method)


class CharacterOutputDevice(OutputDevice):
    """Common class for all character-based OutputDevices."""
    rows = None  # number of columns
    cols = None  # number of rows
    type = ["char"]  # supported output type list

    def cursor(self):
        """
        Enables the cursor.
        """
        raise NotImplementedError

    def noCursor(self):
        """
        Disables the cursor.
        """
        raise NotImplementedError

    def setCursor(self, row, column):
        """
        Sets the cursor's position.
        """
        raise NotImplementedError

    def display_data(self, *data):
        """
        A function that is called to show text on the display.
        Each positional argument is one like of text.
        """
        raise NotImplementedError


class GraphicalOutputDevice(OutputDevice):
    """Common class for all graphical OutputDevices."""
    height = None  # height of display in pixels
    width = None  # width of display in pixels
    type = ["b&w"]  # supported output type list
    device_mode = "1"  # a "mode" parameter for PIL
    char_height = 8 # height of the default font
    char_width = 8 # width of the default font

    current_image = None #an attribute for storing the currently displayed image

    def display_data_onto_image(self, *args, **kwargs):
        """
        A function that draws text on a PIL.Image, emulating
        character displays (to be used with display_data).
        """
        raise NotImplementedError

    def display_image(self, image):
        """
        A function that shows a PIL.Image on the display.
        It also saves it in the current_image attribute.
        """
        raise NotImplementedError

    def clear(self):
        """
        Clears the display, so that there's nothing shown on it.
        """
        raise NotImplementedError

class OutputProxy(CharacterOutputDevice, GraphicalOutputDevice):

    current_image = None
    __cursor_enabled = False
    __cursor_position = (0, 0)

    def __init__(self, context_alias):
        self.context_alias = context_alias

    def _display_image(self, image, **kwargs):
        """
        **kwargs here is because the backlight driver (or other overlays)
        can be passed other arguments
        """
        self.current_image = image

    def _clear(self):
        self.current_image = None

    def _display_data(self, *data):
        cursor_position = self.__cursor_position if self.__cursor_enabled else None
        self.current_image = self.display_data_onto_image(*data, cursor_position=cursor_position)

    def _cursor(self):
        self.__cursor_enabled = True

    def _noCursor(self):
        self.__cursor_enabled = False

    def _setCursor(self, *position):
        self.__cursor_position = position

    def get_current_image(self):
        return self.current_image

    def on_attach(self):
        if self.current_image:
            self.display_image(self.current_image)

def init(output_config):
    # type: (list) -> None
    """ This function is called by main.py to read the output configuration, pick the corresponding drivers and initialize a Screen object. Returns the screen object created. """
    # Currently only the first screen in the config is initialized
    screen_config = output_config[0]
    driver_name = screen_config["driver"]
    driver_module = importlib.import_module("output.drivers." + driver_name)
    args = screen_config["args"] if "args" in screen_config else []
    kwargs = screen_config["kwargs"] if "kwargs" in screen_config else {}
    return driver_module.Screen(*args, **kwargs)

if __name__ == "__main__":
    o = type("OD", (GraphicalOutputDevice, CharacterOutputDevice), {})()
    op = type("OP", (o.__class__, ), {})()
    o.init_proxy(op)
