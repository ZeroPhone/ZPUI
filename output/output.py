import importlib

screen = None


class OutputDevice(object):
    def __init__(self):
        """Common class for all OutputDevices, such as Screens and emulator"""
        self.rows = None  # number of columns
        self.cols = None  # number of rows


def init(output_config):
    # type: (list) -> None
    """ This function is called by main.py to read the output configuration, pick the corresponding drivers and initialize a Screen object.

    It also sets ``screen`` global of ``output`` module with created ``Screen`` object."""
    global screen
    # Currently only the first screen in the config is initialized
    screen_config = output_config[0]  # todo: why a list ?
    driver_name = screen_config["driver"]
    driver_module = importlib.import_module("output.drivers." + driver_name)
    args = screen_config["args"] if "args" in screen_config else []
    kwargs = screen_config["kwargs"] if "kwargs" in screen_config else {}
    screen = driver_module.Screen(*args, **kwargs)
