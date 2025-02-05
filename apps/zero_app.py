class ZeroApp(object):
    """
    A template class for a Zerophone App. Presents default functions that are called by the app manager.
    Keeps a pointer to the input and output devices
    """

    def __init__(self, i, o):
        """Constructor : called when the ZPUI boots. Avoid loading too many objects here. The application is not yet
        opened. Without knowing if you app will be used, do not burden the poor CPU with unused stuff."""
        # type: (InputListener, object) -> ZeroApp
        self.__output = o
        self.__input = i
        if not hasattr(self, "menu_name"):
            self.menu_name = "ZeroApp template"  # Name as presented in the menu
        if hasattr(self, "init_app"):
            self.init_app()

    def init_app(self):
        """
        After-constructor function. Equivalent to __init__ but you don't need to call `super()` or
        manage ``i`` and ``o``. In short, just use this one unless you need to do wacky ``i/o`` 
        obj management stuff, and even then, you probably don't need to redefine ``__init__``!
        """
        pass

    @property
    def i(self):
        return self.__input

    @property
    def o(self):
        return self.__output
