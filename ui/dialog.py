from time import sleep
from helpers import setup_logger
from funcs import format_for_screen as ffs

from base_ui import BaseUIElement
from base_view_ui import BaseViewMixin, BaseView
from canvas import Canvas

logger = setup_logger(__name__, "info")

class DialogBox(BaseViewMixin, BaseUIElement):
    """Implements a dialog box with given values (or some default ones if chosen)."""

    value_selected = False
    selected_option = 0
    default_options = {"y":["Yes", True], 'n':["No", False], 'c':["Cancel", None]}
    start_option = 0

    config_key = "dialog"
    default_pixel_view = "GraphicalView"
    default_char_view = "TextView"

    def __init__(self, values, i, o, message="Are you sure?", name="DialogBox", config={}):
        """Initialises the DialogBox object.

        Args:

            * ``values``: values to be used. Should be a list of ``[label, returned_value]`` pairs.

              * You can also pass a string "yn" to get "Yes(True), No(False)" options, or "ync" to get "Yes(True), No(False), Cancel(None)" options.
              * Values put together with spaces between them shouldn't be longer than the screen's width.

            * ``i``, ``o``: input&output device objects

        Kwargs:

            * ``message``: Message to be shown on the first line of the screen when UI element is activated
            * ``name``: UI element name which can be used internally and for debugging.

        """
        BaseUIElement.__init__(self, i, o, name)
        if isinstance(values, basestring):
            self.values = []
            for char in values:
                self.values.append(self.default_options[char])
            #value_str = " ".join([value[0] for value in values])
            #assert(len(value_str) <= o.cols, "Resulting string too long for the display!")
        else:
            if not type(values) in (list, tuple):
                raise ValueError("Unsupported 'values' argument - needs a list, supplied {}".format(repr(values)))
            if not values:
                raise ValueError("Empty/invalid 'values' argument!")
            for i, value in enumerate(values):
                if isinstance(value, basestring) and value in self.default_options:
                    #"y", "n" or "c" supplied as a shorthand for one of three default arguments
                    values[i] = self.default_options[value]
            self.values = values
        self.message = message
        BaseViewMixin.__init__(self, config=config)

    def generate_views_dict(self):
        return {
            "TextView": TextView,
            "GraphicalView": GraphicalView}

    def set_start_option(self, option_number):
        """
        Allows you to set position of the option that'll be selected upon DialogBox activation.
        """
        self.start_option = option_number

    def before_activate(self):
        self.value_selected = False
        self.selected_option = self.start_option

    @property
    def is_active(self):
        return self.in_foreground

    def get_return_value(self):
        if self.value_selected:
            return self.values[self.selected_option][1]
        else:
            return None

    def idle_loop(self):
        sleep(0.1)

    def generate_keymap(self):
        return {
        "KEY_RIGHT": 'move_right',
        "KEY_LEFT": 'move_left',
        "KEY_ENTER": 'accept_value'
        }

    def move_left(self):
        if self.selected_option == 0:
            self.deactivate()
            return
        self.selected_option -= 1
        self.refresh()

    def move_right(self):
        if self.selected_option == len(self.values)-1:
            return
        self.selected_option += 1
        self.refresh()

    def accept_value(self):
        self.value_selected = True
        self.deactivate()


class TextView(BaseView):

    def __init__(self, o, el):
        BaseView.__init__(self, o, el)
        self.process_values()

    def process_values(self):
        labels = [label for label, value in self.el.values]
        label_string = " ".join(labels)
        if len(label_string) > self.o.cols:
            raise ValueError("DialogBox {}: all values combined are longer than screen's width".format(self.el.name))
        self.right_offset = (self.o.cols - len(label_string))/2
        self.displayed_label = " "*self.right_offset+label_string
        #Need to go through the string to mark the first places because we need to remember where to put the cursors
        current_position = self.right_offset
        self.positions = []
        for label in labels:
            self.positions.append(current_position)
            current_position += len(label) + 1

    def get_cursor_pos(self):
        return (1, self.positions[self.el.selected_option])

    def get_displayed_data(self):
        return [self.el.message, self.displayed_label]

    def refresh(self):
        return self.character_refresh()

class GraphicalView(TextView):

    def get_displayed_image(self):
        c = Canvas(self.o)
        #Drawing text
        chunk_y = 0
        formatted_message = ffs(self.el.message, self.o.cols)
	if len(formatted_message)*(self.o.char_height+2) > self.o.height - self.o.char_height - 2:
                raise ValueError("DialogBox {}: message is too long to fit on the screen".format(self.el.name))
        for line in formatted_message:
                c.text(line, (0, chunk_y))
                chunk_y += self.o.char_height + 2
        c.text(self.displayed_label, (2, chunk_y))

        #Calculating the cursor dimensions
        first_char_position = self.positions[self.el.selected_option]
        option_length = len( self.el.values[self.el.selected_option][0] )
        c_x1 = first_char_position * self.o.char_width
        c_x2 = c_x1 + option_length * self.o.char_width
        c_y1 = chunk_y #second line
        c_y2 = c_y1 + self.o.char_height
        #Some readability adjustments
        cursor_dims = ( c_x1, c_y1, c_x2 + 2, c_y2 + 2 )

        #Drawing the cursor
        c.invert_rect(cursor_dims)
        return c.get_image()

    def refresh(self):
        return self.graphical_refresh()
