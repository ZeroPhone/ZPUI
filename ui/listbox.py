from helpers import setup_logger
logger = setup_logger(__name__, "warning")

from ui.base_list_ui import BaseListUIElement, to_be_foreground
from ui.entry import Entry

class Listbox(BaseListUIElement):
    """Implements a listbox to choose one thing from many.

    Attributes:

    * ``contents``: list of listbox entries

      Listbox entry is a list, where:
         * ``entry[0]`` (entry's label) is usually a string which will be displayed in the UI, such as "Option 1". If ``entry_height`` > 1, can be a list of strings, each of those strings will be shown on a separate display row.
         * ``entry[1]`` (entry's value) is the value to be returned when entry is selected. If it's not supplied, entry's label is returned instead.

      You can also pass ``Entry`` objects as entries - ``text`` will be used as label and ``name`` will be used as name.

      *If you want to set contents after the initalisation, please, use set_contents() method.*
    * ``pointer``: currently selected entry's number in ``self.contents``.
    * ``in_foreground`` : a flag which indicates if listbox is currently displayed. If it's not set, inhibits any of listboxes actions which can interfere with other UI element being displayed.

    """
    selected_entry = None
    exit_entry = ["Exit", None]

    def __init__(self, *args, **kwargs):
        """Initialises the Listbox object.

        Args:

            * ``contents``: listbox contents
            * ``i``, ``o``: input&output device objects

        Kwargs:

            * ``name``: listbox name which can be used internally and for debugging.
            * ``selected``: value (that is, ``entry[1]``) of the element to be selected. If no element with this value is found, this is ignored.
            * ``entry_height``: number of display rows one listbox entry occupies.
            * ``append_exit``: appends an "Exit" entry to listbox.

        """
        selected = kwargs.pop("selected", None)
        exitable = kwargs.pop("exitable", None)
        BaseListUIElement.__init__(self, *args, **kwargs)
        if len(self.contents) == 0:
            raise ValueError("A listbox can't be empty!")
        if selected:
            self.go_to_value(selected)
        if exitable:
            logger.warning("Listbox ignores the 'exitable' argument!")

    def get_return_value(self):
        if self.selected_entry is None:
            return None
        entry = self.contents[self.selected_entry]
        if isinstance(entry, Entry):
            return entry.name if entry.name is not None else entry.text
        elif len(entry) == 1:
            return entry[0]
        else:
            return entry[1]

    def process_contents(self):
        BaseListUIElement.process_contents(self)
        # Replacing string-based entry labels with single-element lists
        for i, entry in enumerate(self.contents):
            if isinstance(entry, basestring):
                self.contents[i] = [entry]
        logger.debug("{}: contents processed".format(self.name))

    @to_be_foreground
    def select_entry(self):
        """ Gets the currently specified entry's index and sets it as selected_entry attribute.
        |Is typically used as a callback from input event processing thread."""
        logger.debug("entry selected")
        self.selected_entry = self.pointer
        self.deactivate()

    def go_to_value(self, value):
        """
        Moves the pointer to the first entry which has the value passed.
        """
        for i, entry in enumerate(self.contents):
            if isinstance(entry, Entry):
              if entry.name == value or (entry.name is None and entry.text == value):
                self.start_pointer = i
                return
            elif (len(entry) > 1 and entry[1] == value) or entry[0] == value:
                self.start_pointer = i
                return
