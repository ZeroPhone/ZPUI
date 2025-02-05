"""Contains base classes for UI elements that deal with lists of entries, that can be scrolled through using arrow keys.
Best example of such an element is a Menu element - it has menu entries you can scroll through, which execute a callback
 when you click on them. """

from copy import copy
from time import sleep
from threading import Event

from ui.entry import Entry
from ui.canvas import Canvas
from ui.base_ui import BaseUIElement
from ui.utils import to_be_foreground, clamp_list_index
from helpers import setup_logger

logger = setup_logger(__name__, "warning")

global_config = {}

# Documentation building process has problems with this import
try:
    import ui.config_manager as config_manager
except (ImportError, AttributeError):
    pass
else:
    cm = config_manager.get_ui_config_manager()
    cm.set_path("ui/configs")
    try:
        global_config = cm.get_global_config()
    except OSError as e:
        logger.error("Config files not available, running under ReadTheDocs?")
        logger.exception(e)


class BaseListUIElement(BaseUIElement):
    """This is a base UI element for list-like UI elements.
       This UI element has the ability to go into background. It's usually for the cases when
       an UI element can call another UI element, after the second UI element returns,
       context has to return to the first UI element - like in nested menus.

       This UI element has built-in scrolling of entries - if the entry text is longer
       than the screen, once the entry is selected, UI element will scroll through its text."""

    contents = []
    pointer = 0
    start_pointer = 0
    in_foreground = False
    exit_entry = ["Back", "exit"]

    config_key = "base_list_ui"
    view_mixin = None

    def __init__(self, contents, i, o, name=None, entry_height=1, append_exit=True, exitable=True, scrolling=True,
                 config=None, keymap=None, override_left=True):
        self.exitable = exitable
        self.custom_keymap = keymap if keymap else {}
        BaseUIElement.__init__(self, i, o, name, input_necessary=True, override_left=override_left)
        self.entry_height = entry_height
        self.append_exit = append_exit
        self.scrolling = {
            "enabled": scrolling,
            "current_scrollable": False
        }
        self.scrolling_defaults = {
            "current_finished": False,
            "current_speed": 1,
            "counter": 0,
            "pointer": 0
        }
        self.reset_scrolling()
        self.config = config if config is not None else global_config
        self.set_view(self.config.get(self.config_key, {}))
        self.set_contents(contents)
        self.inhibit_refresh = Event()

    def set_views_dict(self):
        self.views = {
            "TextView": TextView,
            "EightPtView": EightPtView,
            "SixteenPtView": SixteenPtView,
            "MainMenuTripletView": MainMenuTripletView,
            "PrettyGraphicalView": SixteenPtView,  # Not a descriptive name - left for compatibility
            "SimpleGraphicalView": EightPtView  # Not a descriptive name - left for compatibility
        }
        if self.view_mixin:
            class_name = self.__class__.__name__
            for view_name, view_class in self.views.items():
                if view_class.use_mixin:
                    name = "{}-{}".format(view_name, class_name)
                    logger.debug("Subclassing {} into {}".format(view_name, name))
                    self.views[view_name] = type(name, (self.view_mixin, view_class), {})

    def set_view(self, config):
        view = None
        self.set_views_dict()
        if self.name in config.get("custom_views", {}).keys():
            view_config = config["custom_views"][self.name]
            if isinstance(view_config, basestring):
                if view_config not in self.views:
                    logger.warning('Unknown view "{}" given for UI element "{}"!'.format(view_config, self.name))
                else:
                    view = self.views[view_config]
            elif isinstance(view_config, dict):
                raise NotImplementedError
                # This is the part where fine-tuning views will be possible,
                # once passing args&kwargs is implemented, that is
            else:
                logger.error(
                    "Custom view description can only be a string or a dictionary; is {}!".format(type(view_config)))
        elif not view and "default" in config:
            view_config = config["default"]
            if isinstance(view_config, basestring):
                if view_config not in self.views:
                    logger.warning('Unknown view "{}" given for UI element "{}"!'.format(view_config, self.name))
                else:
                    view = self.views[view_config]
            elif isinstance(view_config, dict):
                raise NotImplementedError  # Again, this is for fine-tuning
        elif not view:
            view = self.get_default_view()
        self.view = view(self.o, self)

    def get_default_view(self):
        """Decides on the view to use for UI element when config file has
        no information on it."""
        if "b&w" in self.o.type:
            return self.views["SixteenPtView"]
        elif "char" in self.o.type:
            return self.views["TextView"]
        else:
            raise ValueError("Unsupported display type: {}".format(repr(self.o.type)))

    def before_activate(self):
        """
        Hook for child UI elements, meant to be called.
        For a start, resets the ``pointer`` to the ``start_pointer``.
        """
        self.pointer = self.start_pointer

    def to_foreground(self):
        """ Is called when UI element's ``activate()`` method is used, sets flags
            and performs all the actions so that UI element can display its contents
            and receive keypresses. Also, refreshes the screen."""
        self.reset_scrolling()
        BaseUIElement.to_foreground(self)

    def idle_loop(self):
        """Contains code which will be executed in UI element's idle loop.
        By default, is just a 0.1 second sleep and a ``scroll()`` call. """
        sleep(0.1)
        self.scroll()

    @property
    def is_active(self):
        return self.in_background

    # Scroll functions - will likely be moved into a mixin or views later on

    @to_be_foreground
    def scroll(self):
        if self.scrolling["enabled"] and not self.scrolling["current_finished"] and self.scrolling["current_scrollable"]:
            self.scrolling["counter"] += 1
            if self.scrolling["counter"] == 10:
                self.scrolling["pointer"] += self.scrolling["current_speed"]
                self.scrolling["counter"] = 0
                self.refresh()

    def reset_scrolling(self):
        self.scrolling.update(self.scrolling_defaults)

    # Debugging helpers - you can set them as callbacks for keys you don't use

    def print_contents(self):
        """ A debug method. Useful for hooking up to an input event so that
            you can see the representation of current UI element's contents. """
        logger.info(self.contents)

    # Callbacks for moving up and down in the entry list

    @to_be_foreground
    def move_down(self):
        """ Moves the pointer one entry down, if possible.
        |Is typically used as a callback from input event processing thread.
        |TODO: support going from bottom to top when pressing "down" with
        last entry selected."""
        if self.pointer < (len(self.contents) - 1):
            logger.debug("moved down")
            self.pointer += 1
            self.reset_scrolling()
            self.refresh()
            return True
        else:
            return False

    @to_be_foreground
    def page_down(self, counter=None):
        """ Scrolls up a full screen of entries, if possible.
            If not possible, moves as far as it can."""
        if not counter:
            counter = self.view.get_entry_count_per_screen()
        self.inhibit_refresh.set()
        while counter != 0 and self.pointer < (len(self.contents) - 1):
            counter -= 1
            self.move_down()
        self.inhibit_refresh.clear()
        self.refresh()
        self.reset_scrolling()
        return True

    @to_be_foreground
    def move_up(self):
        """ Moves the pointer one entry up, if possible.
        |Is typically used as a callback from input event processing thread.
        |TODO: support going from top to bottom when pressing "up" with
        first entry selected."""
        if self.pointer != 0:
            logger.debug("moved up")
            self.pointer -= 1
            self.refresh()
            self.reset_scrolling()
            return True
        else:
            return False

    @to_be_foreground
    def page_up(self, counter=None):
        """ Scrolls down a full screen of UI entries, if possible.
            If not possible, moves as far as it can."""
        if not counter:
            counter = self.view.get_entry_count_per_screen()
        self.inhibit_refresh.set()
        while counter != 0 and self.pointer != 0:
            counter -= 1
            self.move_up()
        self.inhibit_refresh.clear()
        self.refresh()
        self.reset_scrolling()
        return True

    @to_be_foreground
    def move_to_start(self, counter=None):
        """ Goes to the first entry if not already there. """
        if self.pointer != 0:
            logger.debug("moved to start")
            self.pointer = 0
            self.refresh()
            self.reset_scrolling()
            return True
        else:
            return False

    @to_be_foreground
    def move_to_end(self):
        """ Goes to the last entry if not already there. """
        if self.pointer != len(self.contents)-1:
            logger.debug("moved to end")
            self.pointer = len(self.contents)-1
            self.refresh()
            self.reset_scrolling()
            return True
        else:
            return False

    @to_be_foreground
    def select_entry(self):
        """To be overridden by child UI elements. Is executed when ENTER is pressed
           in UI element."""
        logger.debug("Enter key press detected on {}".format(self.contents[self.pointer]))

    @to_be_foreground
    def process_right_press(self):
        """To be overridden by child UI elements. Is executed when RIGHT is pressed
           in UI element."""
        logger.debug("Right key press detected on {}".format(self.contents[self.pointer]))

    # Working with the keymap

    def generate_keymap(self):
        """Makes the keymap dictionary for the input device."""
        return {
            "KEY_UP": "move_up",
            "KEY_DOWN": "move_down",
            "KEY_F3": "page_up",
            "KEY_F4": "page_down",
            "KEY_HOME": "move_to_start",
            "KEY_END": "move_to_end",
            "KEY_ENTER": "select_entry",
            "KEY_RIGHT": "process_right_press"
        }

    def set_keymap(self, keymap):
        if self.exitable and self._override_left:
            keymap["KEY_LEFT"] = "deactivate"
        # BaseUIElement.process_contents ignores self.exitable
        # and only honors self._override_left
        # Let's save it to a temp variable and process the contents!
        override_left = self._override_left
        self._override_left = False
        keymap.update(self.custom_keymap)
        BaseUIElement.set_keymap(self, keymap)
        # Restoring self._override_left
        self._override_left = override_left

    def set_contents(self, contents):
        """Sets the UI element contents and triggers pointer recalculation in the view."""
        self.validate_contents(contents)
        # Copy-ing the contents list is necessary because it can be modified
        # by UI elements that are based on this class
        self.contents = copy(contents)
        self.process_contents()
        self.view.fix_pointers_on_contents_update()

    def validate_contents(self, contents):
        """A hook to validate contents before they're set. If validation is unsuccessful,
        raise exceptions (it's better if exception message contains the faulty entry).
        Does not check if the contents are falsey."""
        # if not contents:
        #    raise ValueError("UI element 'contents' argument has to be set to a non-empty list!")
        for entry in contents:
            if isinstance(entry, Entry):
                pass # We got an Entry object, we don't validate those yet
            else:
                entry_repr = entry[0]
                if not isinstance(entry_repr, basestring) and not isinstance(entry_repr, list):
                    raise Exception("Entry labels can be either strings or lists of strings - {} is neither!".format(entry))
                if isinstance(entry_repr, list):
                    for entry_str in entry_repr:
                        if not isinstance(entry_str, basestring):
                            raise Exception("List entries can only contain strings - {} is not a string!".format(entry_str))

    def process_contents(self):
        """Processes contents for custom callbacks. Currently, only 'exit' calbacks are supported.

        If ``self.append_exit`` is set, it goes through the menu and removes every callback which either is ``self.deactivate`` or is just a string 'exit'.
        |Then, it appends a single "Exit" entry at the end of menu contents. It makes dynamically appending entries to menu easier and makes sure there's only one "Exit" callback, at the bottom of the menu."""
        if self.append_exit:
            # filtering possible duplicate exit entries
            for entry in self.contents:
                if not isinstance(entry, Entry):
                    if len(entry) > 1 and entry[1] == 'exit':
                        self.contents.remove(entry)
            self.contents.append(self.exit_entry)
        logger.debug("{}: contents processed".format(self.name))

    def get_displayed_contents(self):
        """
        This function is to be used for views, in case an UI element wants to
        display entries differently than they're stored (for example, this is used
        in ``NumberedMenu``).
        """
        return self.contents

    def add_view_wrapper(self, wrapper):
        self.view.wrappers.append(wrapper)

    @to_be_foreground
    def refresh(self):
        """ A placeholder to be used for BaseUIElement. """
        if self.inhibit_refresh.isSet():
            return False
        self.view.refresh()
        return True


# Views.

class TextView(object):
    use_mixin = True
    first_displayed_entry = 0
    scrolling_speed_divisor = 4
    fde_increment = 1
    # Default wrapper

    def __init__(self, o, ui_element):
        self.o = o
        self.el = ui_element
        self.entry_height = self.el.entry_height
        self.wrappers = []
        self.setup_scrolling()

    def setup_scrolling(self):
        self.el.scrolling_defaults["current_speed"] = self.get_fow_width_in_chars()/self.scrolling_speed_divisor

    @property
    def in_foreground(self):
        # Is necessary so that @to_be_foreground works
        # Is to_be_foreground even necessary here?
        return self.el.in_foreground

    def get_entry_count_per_screen(self):
        return self.get_fow_height_in_chars() // self.entry_height

    def get_fow_width_in_chars(self):
        return self.o.cols

    def get_fow_height_in_chars(self):
        return self.o.rows

    def fix_pointers_on_contents_update(self):
        """Boundary-checks ``pointer``, re-sets the ``first_displayed_entry`` pointer."""
        full_entries_shown = self.get_entry_count_per_screen()
        contents = self.el.get_displayed_contents()
        entry_count = len(contents)

        new_pointer = clamp_list_index(self.el.pointer, contents)  # Makes sure the pointer isn't larger than the entry count
        if new_pointer == self.el.pointer:
            return # Pointer didn't change from clamping, no action needs to be taken

        self.el.pointer = new_pointer
        if self.first_displayed_entry < new_pointer - full_entries_shown:
            self.first_displayed_entry = new_pointer - full_entries_shown

    def fix_pointers_on_refresh(self):
        full_entries_shown = self.get_entry_count_per_screen()
        if self.el.pointer < self.first_displayed_entry:
            logger.debug("Pointer went too far to top, correcting")
            self.first_displayed_entry = self.el.pointer
        while self.el.pointer >= self.first_displayed_entry + full_entries_shown:
            logger.debug("Pointer went too far to bottom, incrementing first_displayed_entry")
            self.first_displayed_entry += self.fde_increment
        logger.debug("First displayed entry is {}".format(self.first_displayed_entry))

    def entry_is_active(self, entry_num):
        return entry_num == self.el.pointer

    def get_displayed_text(self, contents):
        """Generates the displayed data for a character-based output device. The output of this function can be fed to the o.display_data function.
        |Corrects last&first_displayed_entry pointers if necessary, then gets the currently displayed entries' numbers, renders each one 
        of them and concatenates them into one big list which it returns.
        |Doesn't support partly-rendering entries yet."""
        displayed_data = []
        full_entries_shown = self.get_entry_count_per_screen()
        entries_shown = min(len(contents), full_entries_shown)
        disp_entry_positions = range(self.first_displayed_entry, self.first_displayed_entry+entries_shown)
        for entry_num in disp_entry_positions:
            text_to_display = self.render_displayed_entry_text(entry_num, contents)
            displayed_data += text_to_display
        logger.debug("Displayed data: {}".format(displayed_data))
        return displayed_data

    def process_active_entry(self, entry):
        """ This function processes text of the active entry in order to scroll it. """
        avail_display_chars = (self.get_fow_width_in_chars() * self.entry_height)
        # Scrolling only works with strings for now
        # Maybe scrolling should be its own mixin?
        # Likely, yes.
        self.el.scrolling["current_scrollable"] = len(entry) > avail_display_chars
        if not self.el.scrolling["current_scrollable"]:
            return entry
        overflow_amount = len(entry) - self.el.scrolling["pointer"] - avail_display_chars
        if overflow_amount <= -self.el.scrolling["current_speed"]:
            self.el.scrolling["pointer"] = 0
            self.el.scrolling["current_finished"] = True
        elif overflow_amount < 0:
            # If a pointer is clamped, we still need to display the last part
            # - without whitespace
            self.el.scrolling["pointer"] = len(entry) - avail_display_chars
        if self.el.scrolling["current_scrollable"] and not self.el.scrolling["current_finished"]:
            entry = entry[self.el.scrolling["pointer"]:]
        return entry

    def process_inactive_entry(self, entry):
        return entry

    def render_displayed_entry_text(self, entry_num, contents):
        """Renders an UI element entry by its position number in self.contents, determined also by display width, self.entry_height and entry's representation type.
        If entry representation is a string, splits it into parts as long as the display's width in characters.
           If active flag is set, appends a "*" as the first entry's character. Otherwise, appends " ".
           TODO: omit " " and "*" if entry height matches the display's row count.
        If entry representation is a list, it returns that list as the rendered entry, trimming and padding with empty strings when necessary (to match the ``entry_height``).
        """
        rendered_entry = []
        entry = contents[entry_num]
        if isinstance(entry, Entry):
            text = entry.text
        else:
            text = entry[0]
        active = self.entry_is_active(entry_num)
        display_columns = self.get_fow_width_in_chars()
        if isinstance(text, basestring):
            if active:
                text = self.process_active_entry(text)
            else:
                text = self.process_inactive_entry(text)
            rendered_entry.append(text[:display_columns])  # First part of string displayed
            text = text[display_columns:]  # Shifting through the part we just displayed
            for row_num in range(
                    self.entry_height - 1):  # First part of string done, if there are more rows to display, we give them the remains of string
                rendered_entry.append(text[:display_columns])
                text = text[display_columns:]
        elif type(text) == list:
            text = text[
                    :self.entry_height]  # Can't have more arguments in the list argument than maximum entry height
            while len(text) < self.entry_height:  # Can't have less either, padding with empty strings if necessary
                text.append('')
            return [str(entry_str)[:display_columns] for entry_str in text]
        else:
            # Something slipped past the check in set_contents
            raise Exception("Entries may contain either strings or lists of strings as their representations")
        logger.debug("Rendered entry: {}".format(rendered_entry))
        return rendered_entry

    def get_active_line_num(self):
        return (self.el.pointer - self.first_displayed_entry) * self.entry_height

    def refresh(self):
        logger.debug("{}: refreshed data on display".format(self.el.name))
        self.fix_pointers_on_refresh()
        displayed_data = self.get_displayed_text(self.el.get_displayed_contents())
        for wrapper in self.wrappers:
            displayed_data = wrapper(displayed_data)
        self.o.noCursor()
        self.o.display_data(*displayed_data)
        self.o.setCursor(self.get_active_line_num(), 0)
        self.o.cursor()


class EightPtView(TextView):
    charwidth = 6
    charheight = 8
    x_offset = 2
    x_scrollbar_offset = 5
    scrollbar_y_offset = 1
    font = None
    default_full_width_cursor = False

    def __init__(self, *args, **kwargs):
        self.full_width_cursor = kwargs.pop("full_width_cursor", self.default_full_width_cursor)
        TextView.__init__(self, *args, **kwargs)

    def get_fow_width_in_chars(self):
        return (self.o.width - self.x_scrollbar_offset) // self.charwidth

    def get_fow_height_in_chars(self):
        return self.o.height // self.charheight

    def refresh(self):
        logger.debug("{}: refreshed data on display".format(self.el.name))
        self.fix_pointers_on_refresh()
        image = self.get_displayed_image()
        for wrapper in self.wrappers:
            image = wrapper(image)
        self.o.display_image(image)

    def scrollbar_needed(self, contents):
        # No scrollbar if all the entries fit on the screen
        full_entries_shown = self.get_entry_count_per_screen()
        total_entry_count = len(contents)
        return total_entry_count > full_entries_shown

    def get_scrollbar_top_bottom(self, contents):
        if not self.scrollbar_needed(contents):
            return 0, 0
        full_entries_shown = self.get_entry_count_per_screen()
        total_entry_count = len(contents)
        scrollbar_max_length = self.o.height - (self.scrollbar_y_offset * 2)
        entries_before = self.first_displayed_entry
        # Scrollbar length per one entry
        length_unit = float(scrollbar_max_length) / total_entry_count
        top = self.scrollbar_y_offset + int(entries_before * length_unit)
        length = int(full_entries_shown * length_unit)
        bottom = top + length
        return top, bottom

    def draw_scrollbar(self, c, contents):
        scrollbar_coordinates = self.get_scrollbar_top_bottom(contents)
        # Drawing scrollbar, if applicable
        if scrollbar_coordinates == (0, 0):
            # left offset is dynamic and depends on whether there's a scrollbar or not
            left_offset = self.x_offset
        else:
            left_offset = self.x_scrollbar_offset
            y1, y2 = scrollbar_coordinates
            c.rectangle((1, y1, 2, y2))
        return left_offset

    def draw_menu_text(self, c, menu_text, left_offset):
        for i, line in enumerate(menu_text):
            y = (i * self.charheight - 1) if i != 0 else 0
            c.text(line, (left_offset, y), font=self.font)

    def draw_cursor(self, c, menu_text, left_offset):
        cursor_y = self.get_active_line_num()
        # We might not need to draw the cursor if there are no items present
        if cursor_y is not None:
            c_y = cursor_y * self.charheight + 1
            if self.full_width_cursor:
                x2 = c.width
            else:
                menu_texts = menu_text[cursor_y:cursor_y+self.entry_height]
                max_menu_text_len = max([len(t) for t in menu_texts])
                x2 = self.charwidth * max_menu_text_len + left_offset
            cursor_dims = (
                left_offset - 1,
                c_y - 1,
                x2,
                c_y + self.charheight*self.entry_height - 1
            )
            c.invert_rect(cursor_dims)

    def get_displayed_image(self):
        """Generates the displayed data for a canvas-based output device. The output of this function can be fed to the o.display_image function.
        |Doesn't support partly-rendering entries yet."""
        c = Canvas(self.o)
        # Get the display-ready contents
        contents = self.el.get_displayed_contents()
        # Get the menu text
        menu_text = self.get_displayed_text(contents)
        # Drawing the scrollbar (will only be drawn if applicable)
        left_offset = self.draw_scrollbar(c, contents)
        # Drawing the text itself
        self.draw_menu_text(c, menu_text, left_offset)
        # Drawing the cursor
        self.draw_cursor(c, menu_text, left_offset)
        # Returning the image
        return c.get_image()


class SixteenPtView(EightPtView):
    charwidth = 8
    charheight = 16
    font = ("Fixedsys62.ttf", 16)


class MainMenuTripletView(SixteenPtView):
    # TODO: enable scrolling

    use_mixin = False
    charwidth = 8
    charheight = 16

    def __init__(self, *args, **kwargs):
        SixteenPtView.__init__(self, *args, **kwargs)
        self.charheight = self.o.height / 3

    def get_displayed_image(self):
        # This view doesn't have a cursor, instead, the entry that's currently active is in the display center
        contents = self.el.get_displayed_contents()
        pointer = self.el.pointer # A shorthand
        c = Canvas(self.o)
        central_position = (10, 16)
        font = c.load_font("Fixedsys62.ttf", 32)
        current_entry = contents[pointer]
        c.text(current_entry[0], central_position, font=font)
        font = c.load_font("Fixedsys62.ttf", 16)
        if pointer != 0:
            line = contents[pointer - 1][0]
            c.text(line, (2, 0), font=font)
        if pointer < len(contents) - 1:
            line = contents[pointer + 1][0]
            c.text(line, (2, 48), font=font)
        return c.get_image()
