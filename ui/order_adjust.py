from helpers import setup_logger
logger = setup_logger(__name__, "warning")

from ui.base_list_ui import BaseListUIElement, to_be_foreground
from ui.entry import Entry

class OrderAdjust(BaseListUIElement):
    """Implements an UI element to change ordering of a list of things.

    Attributes:

    * ``contents``: list of entries

      Entry is a list, where:
         * ``entry[0]`` (entry's label) is usually a string which will be displayed in the UI, such as "Option 1". If ``entry_height`` > 1, can be a list of strings, each of those strings will be shown on a separate display row.
         * ``entry[1]`` (entry's value) is the value to be returned when entry is selected. If it's not supplied, entry's label is returned instead.

      You can also pass ``Entry`` objects as entries - ``text`` will be used as label and and ``name`` will be used as name.

      *If you want to set contents after the initalisation, please, use set_contents() method.*
    * ``pointer``: currently selected entry's number in ``self.contents``.
    * ``in_foreground`` : a flag which indicates if UI element is currently displayed. If it's not set, inhibits any of UI elements' actions which can interfere with other UI element being displayed.

    """
    confirmed = False
    contents_before_move = None
    accept_entry = ["Accept"]
    entry_is_being_moved = False

    def __init__(self, *args, **kwargs):
        """Initialises the OrderAdjust object.

        Args:

            * ``contents``: list of entries to adjust order for
            * ``i``, ``o``: input&output device objects

        Kwargs:

            * ``name``: UI element's name, to be used internally and for debugging.
            * ``entry_height``: number of display rows one entry occupies.

        """
        selected = kwargs.pop("selected", None)
        kwargs["append_exit"] = False
        kwargs["override_left"] = False
        BaseListUIElement.__init__(self, *args, **kwargs)
        if len(self.contents) == 0:
            raise ValueError("A listbox can't be empty!")

    def get_return_value(self):
        if not self.confirmed:
            return None
        else:
            return [self.get_entry_value(entry) for entry in self.contents \
                                                        if entry != self.accept_entry]

    def get_entry_value(self, entry):
        if isinstance(entry, Entry):
            return entry.name if entry.name is not None else entry.text
        else:
            return entry[1] if len(entry) > 1 else entry[0]

    def process_contents(self):
        # Replacing string-based entry labels with single-element lists
        for i, entry in enumerate(self.contents):
            if isinstance(entry, basestring):
                self.contents[i] = [entry]
        while self.accept_entry in self.contents:
            self.contents.remove(self.accept_entry)
        self.contents.append(self.accept_entry)
        logger.debug("{}: contents processed".format(self.name))

    def generate_keymap(self):
        keymap = BaseListUIElement.generate_keymap(self)
        keymap["KEY_ENTER"] = "on_enter"
        keymap["KEY_LEFT"] = "on_left"
        keymap.pop("KEY_RIGHT")
        return keymap

    @to_be_foreground
    def on_enter(self):
        if self.contents[self.pointer] == self.accept_entry:
            logger.debug("{}: ordering confirmed".format(self.name))
            self.confirmed = True
            self.deactivate()
        else:
            if self.entry_is_being_moved:
                logger.debug("{}: stopped moving entry: {}".format( \
                              self.name, self.contents[self.pointer]))
                self.entry_is_being_moved = False
            else:
                logger.debug("{}: started moving entry: {}".format( \
                              self.name, self.contents[self.pointer]))
                logger.debug("{}: backing up contents in case move is cancelled".format(self.name))
                self.contents_before_move = [e for e in self.contents]
                self.entry_is_being_moved = True
            self.refresh()

    @to_be_foreground
    def on_left(self):
        if self.entry_is_being_moved:
            logger.debug("{}: pressed LEFT while moving, restoring contents".format(self.name))
            self.contents = self.contents_before_move
            self.entry_is_being_moved = False
            self.refresh()
        else:
            self.deactivate()

    @to_be_foreground
    def move_up(self):
        if self.entry_is_being_moved and self.contents[self.pointer] != self.accept_entry:
            if self.pointer > 0:
                logger.debug("{}: moved an entry up: {}".format( \
                              self.name, self.contents[self.pointer]))
                self.contents[self.pointer], self.contents[self.pointer-1] = \
                 self.contents[self.pointer-1], self.contents[self.pointer]
        BaseListUIElement.move_up(self)

    @to_be_foreground
    def move_down(self):
        if self.entry_is_being_moved and self.contents[self.pointer] != self.accept_entry:
            if self.pointer < len(self.contents)-2: # -1 for the "Accept" entry
                logger.debug("{}: moved an entry down: {}".format( \
                              self.name, self.contents[self.pointer]))
                self.contents[self.pointer], self.contents[self.pointer+1] = \
                 self.contents[self.pointer+1], self.contents[self.pointer]
        BaseListUIElement.move_down(self)
