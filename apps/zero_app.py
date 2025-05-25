class ZeroApp(object):
    """
    A template class for a Zerophone App. Presents default functions that are called by the app manager.
    Keeps a pointer to the input and output devices
    """

    def __init__(self, i, o):
        """
        Constructor : called when the ZPUI boots. Avoid loading too many objects here.
        The application is not yet opened. Without knowing if you app will be used,
        do not burden the poor CPU with unused stuff.
        """
        # type: (InputListener, object) -> ZeroApp
        self.__output = o
        self.__input = i
        if not hasattr(self, "menu_name"):
            self.menu_name = "ZeroApp template"  # Name as presented in the menu
        if hasattr(self, "init_app"):
            self.init_app()
        if getattr(self, "wants_context", False):
            if not hasattr(self, "set_context"):
                # placing the default function in an expected spot
                self.set_context = self.__set_context

    def can_load(self):
        """
        Default function for checking if app can load on this platform.
        If app shouldn't be loaded, return False and a string detailing the reason for app not loading.
        Otherwise, return True.

        Can be used for things like hardware-specific apps,
        apps that only work with certain screen typoes and sizes,
        and so on.
        """
        return True

    def __set_context(self, context):
        """
        default function for obtaining context, is used if `wants_context` is set
        """
        self.context = context

    def init_app(self):
        """
        After-constructor function. Equivalent to __init__ but you don't need to call `super()` or
        manage ``i`` and ``o``. In short, just use this one unless you need to do wacky ``i/o``
        obj management stuff (you likely don't), and even then, you probably don't need to redefine ``__init__``!
        """
        pass

    @property
    def i(self):
        return self.__input

    @property
    def o(self):
        return self.__output
