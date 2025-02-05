from threading import Event
from time import sleep

from ui.base_list_ui import BaseListUIElement, to_be_foreground
from ui.loading_indicators import LoadingBar
from ui.utils import clamp, clamp_list_index
from ui.entry import Entry
from helpers import setup_logger

logger = setup_logger(__name__, "warning")


class MenuExitException(Exception):
    """An exception that you can throw from a menu callback to exit the menu that
       the callback was called from (and underlying menus, if necessary)"""
    pass


class Menu(BaseListUIElement):
    """Implements a menu which can be used to navigate through your application,
    output a list of values or select actions to perform. Is one of the most used
    UI elements, used both in system core and in most of the applications."""

    pointer = 0  #: number of currently selected menu entry, starting from 0.
    in_background = False  #: flag which indicates whether menu is currently active, either being displayed or just waiting in background (for example, when you go into a sub-menu, the parent menu will still be considered active).
    in_foreground = False  #: flag which indicates whether menu is currently displayed.
    exit_exception = False

    def __init__(self, *args, **kwargs):
        """Initialises the Menu object.

        Args:

            * ``contents``: list of menu entries which was passed either to ``Menu`` constructor or to ``menu.set_contents()``.

              Simplest ``Menu`` entry is a list, where:
                 * ``entry[0]`` (entry label) is usually a string which will be displayed in the UI, such as "Menu entry 1". If ``entry_height`` > 1, can be a list of strings, each of those strings will be shown on a separate display row.
                 * ``entry[1]`` (entry callback) is a function which is called when the user presses Enter.

                   * Can be omitted if you don't need to have any actions taken upon activation of the entry.
                   * You can supply 'exit' (a string, not a function) if you want a menu entry that exits the menu when the user presses Enter.

                 * ``entry[2]`` (entry second callback) is a callback for the right key press.

              You can also pass ``Entry`` objects as entries - ``text`` will be used as label, ``cb`` will be used as first callback and ``cb2`` will be used as the second callback.

              If you want to set contents after the initialisation, please, use set_contents() method.*
            * ``i``, ``o``: input&output device objects

        Kwargs:

            * ``name``: Menu name which can be used internally and for debugging.
            * ``entry_height``: number of display rows one menu entry occupies.
            * ``append_exit``: Appends an "Exit" element to menu contents.
            * ``catch_exit``: If ``MenuExitException`` is received and catch_exit is False, it passes ``MenuExitException`` to the parent menu so that it exits, too. If catch_exit is True, MenuExitException is not passed along.
            * ``exitable``: Decides if menu can exit by pressing ``KEY_LEFT``. Set by default and disables ``KEY_LEFT`` callback if unset. Is used for ZPUI main menu, not advised to be used in other settings.
            * ``contents_hook``: A function that is called every time menu goes in foreground that returns new menu contents. Allows to almost-dynamically update menu contents.
            * ``on_contents_hook_fail``: A function that is called when ``contents_hook`` raises an exception or returns None. Will be passed two arguments: 1) arg ``self`` (``Menu`` object) 2) kwarg ``exception=bool`` (``True`` or ``False``, whether ``contents_hook`` raised an exception or not).

        """
        self.catch_exit = kwargs.pop("catch_exit", True)
        self.contents_hook = kwargs.pop("contents_hook", None)
        self.on_contents_hook_fail = kwargs.pop("on_contents_hook_fail", None)
        BaseListUIElement.__init__(self, *args, **kwargs)

    def before_activate(self):
        # Clearing flags before the menu is activated
        self.exit_exception = False

    def before_foreground(self):
        self.exec_contents_hook()

    def trigger_contents_hook(self):
        """
        External method to trigger Menu contents update if the contents_hook is set.
        If contents_hook is not set, raises an AttributeError.
        """
        result = self.exec_contents_hook()
        if result is None:
            raise AttributeError("{}: contents_hook is not set!".format(self.name))

    def exec_contents_hook(self):
        """
        Executes ``contents_hook`` and, if successful, sets new contents.
        If ``contents_hook`` failed to execute (or returned ``None``), will see if
        ``on_contents_hook_fail`` attribute is callable and, if it is, calls it.
        Otherwise, deactivates the ``Menu``.
        Returns ``True`` if successful. If failed at any step, returns ``False``.
        If contents_hook is not set, returns ``None``.
        """
        if callable(self.contents_hook):
            try:
                new_contents = self.contents_hook()
            except:
                logger.exception("{}: contents hook raised an exception!".format(self.name))
                if callable(self.on_contents_hook_fail):
                    self.on_contents_hook_fail(self, exception=True)
                else:
                    # Just making the menu exit by deactivating
                    self.deactivate()
                return False
            else:
                if new_contents is not None:
                    self.set_contents(new_contents)
                    return True
                else:
                    if callable(self.on_contents_hook_fail):
                        self.on_contents_hook_fail(self, exception=False)
                    else:
                        logger.error("{}: contents hook returned None, on_contents_hook_fail not set - deactivating".format(self.name))
                        self.deactivate()
                    return False
        else:
            return None

    def get_return_value(self):
        if self.exit_exception:
            if not self.catch_exit:
                logger.info("{} received MenuExitException, raising it further".format(self.name))
                raise MenuExitException

    def get_callback_from_entry(self, entry, callback_number=1):
        if isinstance(entry, Entry):
            attr_names = [None, "cb", "cb2"]
            attr_name = attr_names[callback_number]
            return getattr(entry, attr_name, None)
        else:
            if len(entry) > callback_number:
                return entry[callback_number]
            else:
                return None

    @to_be_foreground
    def select_entry(self, callback_number=1, entry_index=None):
        """ Gets the currently specified entry's description from self.contents and executes the callback, if set.
        |Is typically used as a callback from input event processing thread.
        |After callback's execution is finished, sets the keymap again and refreshes the screen.
        |If MenuExitException is returned from the callback, exits menu."""
        logger.debug("entry selected")
        self.to_background()
        if entry_index != None:
            entry = self.contents[entry_index]
        else:
            entry = self.contents[self.pointer]
        if entry == self.exit_entry:
            # It's the exit entry, exiting
            self.deactivate()
            return
        callback = self.get_callback_from_entry(entry, callback_number=callback_number)
        if callback:
            # Current menu entry has a valid callback
            try:
                callback()
            except MenuExitException:
                self.exit_exception = True
            except Exception as exc:
                logger.exception("{}: Callback raised an exception".format(self.name))
            finally:
                if self.exit_exception:
                    self.deactivate()
                    return
                else:
                    self.reset_scrolling()
                    self.to_foreground()
        else:
            self.reset_scrolling()
            self.to_foreground()

    def process_right_press(self):
        """Calls the second callback on the right button press."""
        self.select_entry(callback_number=2)


class MenuRenderingMixin(object):
    """A mixin to add Menu-specific rendering to views.
    If you're making your own view for BaseListUIElements and want it to
    work with menu UI elements, you will probably want to use this mixin,
    like this:

    .. code-block:: python

        class MeEightPtView(MenuRenderingMixin, EightPtView):
            pass

    """

    def has_second_callback(self, entry):
        if isinstance(entry, Entry):
            if callable(entry.cb2):
                return True
        elif len(entry) > 2 and callable(entry[2]):
            return True
        return False

    def draw_graphic(self, c, index):
        # c is the canvas object
        # draw_graphic is called for each line of text - not menu entry!
        # so, index is the "line number" - assuming 4 lines/display,
        # for entry_height=1, each index will correspond to a menu entry
        # for entry_height=2, indices 0-1 will be used for the first menu entry
        # and 2-3 will be used for the second menu entry
        # hence, the /self.entry_height part
        print(self.first_displayed_entry, index, self.entry_height)
        contents_entry = self.el.contents[self.first_displayed_entry + index//self.entry_height]
        if self.has_second_callback(contents_entry):
            tw, th = self.charwidth // 2, self.charheight // 2
            right_offset = 1
            top_offset = (self.charheight - th) // 2
            coords = (
                (str(-1*(right_offset+tw)), index * self.charheight + top_offset),
                (str(-1*(right_offset+tw)), index * self.charheight + top_offset + th),
                (str(-1*(right_offset)), index * self.charheight + th),
            )
            c.polygon(coords, fill=c.default_color)

    def draw_menu_text(self, c, menu_text, left_offset):
        for i, line in enumerate(menu_text):
            y = (i * self.charheight - 1) if i != 0 else 0
            c.text(line, (left_offset, y), font=self.font)
            if "b&w" in self.o.type:
                self.draw_graphic(c, i)


Menu.view_mixin = MenuRenderingMixin


class MessagesMenu(Menu):
    """
    A modified version of the Menu class
    for displaying a list of messages and loading new ones

    HERE BE DRAGONS
    FORMATTING PROBABLY BROKEN
    PROCEED WITH CAUTION
    """

    load_more_possible = True
    load_more_marker = ["Load more"]

    def __init__(self, *args, **kwargs):
        self.load_more_callback = kwargs.pop("load_more_callback", None)
        self.load_more_trigger_point = kwargs.pop("load_more_trigger_point", 0)
        self.load_more_allow_refresh = Event()
        self.load_more_allow_refresh.set()

        Menu.__init__(self, *args, **kwargs)

    def before_activate(self):
        Menu.before_activate(self)
        self.pointer = clamp(len(self.contents) - 2, 0, len(self.contents)-1)
        if self.contents: # Not empty
            self.add_load_more_marker()

    def add_load_more_marker(self):
        if [self.load_more_marker] not in self.contents:
            self.contents = [self.load_more_marker] + self.contents

    def remove_load_more_marker(self):
        while self.load_more_marker in self.contents:
            self.contents.remove(self.load_more_marker)

    def load_more(self):
        self.load_more_allow_refresh.clear()
        before = len(self.contents)
        self.remove_load_more_marker()
        has_loaded_more_events = True
        contents_added = False
        counter = 0
        li = None
        while has_loaded_more_events and not contents_added:
            if counter == 5: # the user is let down, let's at least show them stuff is happening
                li = LoadingBar(self.i, self.o, message="Loading messages", name="{} - load_more() LoadingBar")
                li.run_in_background()
                has_loaded_more_events = self.load_more_callback()
                logger.debug("Loaded more events!")
                if has_loaded_more_events:
                    self.remove_load_more_marker()
                    self.add_load_more_marker()
                    after = len(self.contents)
            difference = after-before
            if difference > 0:
                contents_added = True
                logger.info("Loaded {} messages".format(difference))
                self.pointer += (after-before)+1
            else:
                logger.info("Loaded events but no messages, retrying")
            self.pointer = clamp_list_index(self.pointer, self.contents)
        else:
            self.remove_load_more_marker()
            counter += 1
        if li: # LoadingBar fired up, need to stop it now
            li.stop()
            sleep(0.5) # until it actually stops =D
            self.activate_input() #reset keymap back to normal
        self.load_more_allow_refresh.set()
        self.refresh()

    @to_be_foreground
    def refresh(self):
        if not self.load_more_allow_refresh.isSet():
            return
        Menu.refresh(self)

    @to_be_foreground
    def move_up(self):
        Menu.move_up(self)

        if self.pointer <= self.load_more_trigger_point:
            self.load_more()
