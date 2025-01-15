from time import sleep

from ui.base_ui import BaseUIElement
from ui.canvas import Canvas
from ui.funcs import format_for_screen as ffs
from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "info")

class DialogBox(BaseUIElement):
    """Implements a dialog box with given values (or some default ones if chosen)."""

    view = None
    value_selected = False
    selected_option = 0
    default_options = {"y":["Yes", True], 'n':["No", False], 'c':["Cancel", None]}
    start_option = 0

    def __init__(self, values, i, o, message="Are you sure?", name="DialogBox", **kwargs):
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
        BaseUIElement.__init__(self, i, o, name, **kwargs)
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
        self.set_view()
        # Keymap will depend on view
        self.set_default_keymap()

    def set_view(self):
        if "b&w" in self.o.type:
            view_class = GraphicalView
        elif "char" in self.o.type:
            view_class = TextView
        else:
            raise ValueError("Unsupported display type: {}".format(repr(self.o.type)))
        self.view = view_class(self.o, self)

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
        km = {"KEY_ENTER": 'accept_value'}
        scroll_is_vertical = getattr(self.view, 'scroll_is_vertical', False)
        if scroll_is_vertical:
            km.update({
              "KEY_DOWN": 'move_right',
              "KEY_UP": 'move_left',
              "KEY_LEFT": 'deactivate',
            })
        else:
            km.update({
              "KEY_RIGHT": 'move_right',
              "KEY_LEFT": 'move_left',
            })
        return km

    def move_left(self):
        scroll_is_vertical = getattr(self.view, 'scroll_is_vertical', False)
        if self.selected_option == 0:
            if not scroll_is_vertical:
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

    def refresh(self):
        self.view.refresh()


class TextView(object):

    def __init__(self, o, el):
        self.o = o
        self.el = el
        self.process_values()

    def process_values(self):
        labels = [label for label, value in self.el.values]
        label_string = " ".join(labels)
        if len(label_string) > self.o.cols:
            raise ValueError("DialogBox {}: all values combined are longer than screen's width".format(self.el.name))
        self.right_offset = (self.o.cols - len(label_string))//2
        self.displayed_label = " "*self.right_offset+label_string
        #Need to go through the string to mark the first places because we need to remember where to put the cursors
        labels = [label for label, value in self.el.values]
        current_position = self.right_offset
        self.positions = []
        for label in labels:
            self.positions.append(current_position)
            current_position += len(label) + 1

    def refresh(self):
        self.o.noCursor()
        self.o.setCursor(1, self.positions[self.el.selected_option])
        self.o.display_data(self.el.message, self.displayed_label)
        self.o.cursor()

class GraphicalView(TextView):

    scroll_is_vertical = True

    def process_values(self):
        self.positions = []
        labels = [label for label, value in self.el.values]
        for label in labels:
            label_width = len(label)*self.o.char_width
            label_start = (self.o.width - label_width)//2
            if label_start < 0: label_start = 0
            self.positions.append(label_start)

    def get_image(self):
        c = Canvas(self.o)
        #Drawing text
        chunk_y = 0
        formatted_message = ffs(self.el.message, self.o.cols)
        if len(formatted_message)*(self.o.char_height+2) > self.o.height - self.o.char_height - 2:
            raise ValueError("DialogBox {}: message is too long to fit on the screen: {}".format(self.el.name, formatted_message))
        for line in formatted_message:
            c.text(line, (0, chunk_y))
            chunk_y += self.o.char_height + 2
        first_label_y = chunk_y
        for i, value in enumerate(self.el.values):
            label = value[0]
            label_start = self.positions[i]
            c.text(label, (label_start, chunk_y))
            chunk_y += self.o.char_height + 2

        #Calculating the cursor dimensions
        first_char_x = self.positions[self.el.selected_option]
        option_length = len( self.el.values[self.el.selected_option][0] ) * self.o.char_width
        c_x1 = first_char_x - 2
        c_x2 = c_x1 + option_length + 2
        c_y1 = first_label_y + self.el.selected_option*(2 + self.o.char_height)
        c_y2 = c_y1 + self.o.char_height
        #Some readability adjustments
        cursor_dims = ( c_x1, c_y1, c_x2 + 2, c_y2 + 2 )

        #Drawing the cursor
        c.invert_rect(cursor_dims)
        return c.get_image()

    def refresh(self):
        self.o.display_image(self.get_image())
