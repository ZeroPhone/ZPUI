from functools import wraps
from threading import Event

from canvas import Canvas
from utils import Rect
from entry import Entry

from PIL import Image
Image = Image.Image

class BaseOverlayWithTimeout(object):

    active = False
    counter = 0

    def __init__(self, duration = 20):
        self.duration = duration

    def apply_to(self, ui_el):
        self.wrap_before_foreground(ui_el)
        self.wrap_idle_loop(ui_el)

    def update_state(self, ui_el):
        raise NotImplementedException

    def wrap_idle_loop(self, ui_el):
        idle_loop = ui_el.idle_loop
        @wraps(idle_loop)
        def wrapper(*args, **kwargs):
            return_value = idle_loop(*args, **kwargs)
            self.update_state(ui_el)
            return return_value
        ui_el.idle_loop = wrapper

    def wrap_before_foreground(self, ui_el):
        before_foreground = ui_el.before_foreground
        @wraps(before_foreground)
        def wrapper(*args, **kwargs):
            return_value = before_foreground(*args, **kwargs)
            self.active = True
            self.counter = 0
            return return_value
        ui_el.before_foreground = wrapper


class HelpOverlay(BaseOverlayWithTimeout):
    """
    A screen overlay that hooks onto an UI element, allowing you to show a help
    overlay when a button (by default, F5) is pressed.
    """
    top_offset = 0
    right_offset = 20
    t_top_offset = -2
    t_right_offset = -1

    def __init__(self, callback, key = "KEY_F5", **kwargs):
        self.callbacks = [callback]
        self.key = key
        BaseOverlayWithTimeout.__init__(self, **kwargs)

    def apply_to(self, ui_el):
        self.update_keymap(ui_el)
        self.wrap_view(ui_el)
        BaseOverlayWithTimeout.apply_to(self, ui_el)

    def update_keymap(self, ui_el):
        key, callback = self.get_key_and_callback()
        ui_el.update_keymap({key:callback})

    def wrap_view(self, ui_el):
        def wrapper(image):
            if isinstance(image, Image):
                image = self.modify_image_if_needed(ui_el, image)
            return image
        ui_el.add_view_wrapper(wrapper)

    def push_callback(self, callback):
        self.callbacks.append(callback)

    def pop_callback(self):
        self.callbacks = self.callbacks[:-1]

    def update_state(self, ui_el):
        if self.active:
            self.counter += 1
            if self.counter == self.duration:
                self.active = False
                ui_el.refresh()

    def get_key_and_callback(self):
        return self.key, self.callbacks[-1]

    def modify_image_if_needed(self, ui_el, image):
        if self.active:
            c = Canvas(ui_el.o, base_image=image)
            self.draw_icon(c)
            image = c.get_image()
        return image

    def draw_icon(self, c):
        c.clear((str(-(self.right_offset+c.o.char_width)), self.top_offset, str(-self.right_offset), self.top_offset+c.o.char_height))
        c.text("H", ( str(-(self.right_offset+c.o.char_width+self.t_right_offset)), self.top_offset+self.t_top_offset ))


class FunctionOverlay(HelpOverlay):
    """
    A screen overlay that hooks onto an UI element, allowing you to execute actions
    when buttons (by default, "F1" and "F2") are pressed.
    """
    font = None
    bottom_offset = 10
    right_offset = 0
    t_top_offset = -2
    t_right_offset = -1
    default_keys = ["KEY_F1", "KEY_F2"]
    num_keys = len(default_keys)

    def __init__(self, keymap, labels=["Exit", "Options"], **kwargs):
        if isinstance(keymap, (list, tuple)):
            # Can also pass a list of functions instead of a keymap dict
            # The list will then be mapped to the default keys
            if len(keymap) > len(self.default_keys):
                raise ValueError("Can't use a shorthand - passed {} callback with {} default keys!".format(len(keymap), len(self.default_keys)))
            self.keymap = {}
            for i, cb in enumerate(keymap):
                self.keymap[self.default_keys[i]] = cb
        else:
            self.keymap = keymap
        self.labels = labels
        BaseOverlayWithTimeout.__init__(self, **kwargs)

    def update_keymap(self, ui_el):
        ui_el.update_keymap(self.keymap)

    def wrap_generate_keymap(self, ui_el):
        generate_keymap = ui_el.generate_keymap
        @wraps(generate_keymap)
        def wrapper(*args, **kwargs):
            keymap = generate_keymap(*args, **kwargs)
            keymap.update(self.keymap)
            return keymap
        ui_el.generate_keymap = wrapper
        ui_el.set_default_keymap()

    def draw_icon(self, c):
        half_line_length = c.o.cols/len(self.labels)
        last_line = "".join([label.center(half_line_length) for label in self.labels])
        c.clear((self.right_offset, str(-self.bottom_offset), c.width-self.right_offset, c.height))
        c.text(last_line, (self.right_offset, str(-self.bottom_offset)), font=self.font)


class GridMenuSidebarOverlay(object):

    def __init__(self, sidebar_cb, top_o = None, bottom_o = None, left_o = None, right_o = None):
        self.sidebar_cb = sidebar_cb
        self.top_o = top_o
        self.bottom_o = bottom_o
        self.left_o = left_o
        self.right_o = right_o

    def apply_to(self, ui_el):
        if self.get_sidebar_coords(ui_el) is None:
            raise AttributeError("No coordinate attribute supplied and overlay can't determine them by itself!")
        self.wrap_view(ui_el)

    def get_coords_for_unrecognized_ui_el(self, ui_el):
        return None

    def wrap_view(self, ui_el):
        def wrapper(image):
            if isinstance(image, Image):
                image = self.modify_image(ui_el, image)
            return image
        ui_el.add_view_wrapper(wrapper)

    def modify_image(self, ui_el, image):
        c = Canvas(ui_el.o, base_image=image)
        coords = self.get_sidebar_coords(ui_el)
        self.draw_sidebar(c, ui_el, coords)
        image = c.get_image()
        return image

    def get_sidebar_coords(self, ui_el):
        if self.top_o is None and self.bottom_o is None \
          and self.left_o is None and self.right_o is None:
            # Let's see if we're being applied on a GridMenu-like thing, fail otherwise
            entry_width = getattr(ui_el.view, "entry_width", None)
            cols = getattr(ui_el, "cols", None)
            if not entry_width and not cols:
                return self.get_coords_for_unrecognized_ui_el(ui_el)
            else:
                # Simplified case - GridMenu with a sidebar on the right
                left_offset = ui_el.view.entry_width*ui_el.cols
                sidebar_width = ui_el.o.width-left_offset
                return Rect(left_offset, 0, ui_el.o.width-1, ui_el.o.height)
        else:
            return Rect(self.left_o, self.top_o, self.right_o, self.bottom_o)

    def draw_sidebar(self, c, ui_el, coords):
        return self.sidebar_cb(c, ui_el, coords)


class GridMenuLabelOverlay(HelpOverlay):

    def __init__(self, font = None, text_border = 2, **kwargs):
        BaseOverlayWithTimeout.__init__(self, **kwargs)
        self.text_border = text_border
        self.font = font
        self.is_clear_refresh = Event()

    def get_current_entry_text(self, ui_el):
        contents = ui_el.get_displayed_contents()
        entry = contents[ui_el.pointer]
        if isinstance(entry, Entry):
            return entry.text
        else:
            return entry[0]

    def apply_to(self, ui_el):
        self.wrap_view(ui_el)
        self.wrap_refresh(ui_el)
        self.wrap_idle_loop(ui_el)

    def update_state(self, ui_el):
        if self.active:
            self.counter += 1
            if self.counter == self.duration:
                self.active = False
                self.is_clear_refresh.set()
                ui_el.refresh()

    def wrap_view(self, ui_el):
        def wrapper(image):
            if isinstance(image, Image):
                image = self.modify_image_if_needed(ui_el, image)
            return image
        ui_el.add_view_wrapper(wrapper)

    def wrap_refresh(self, ui_el):
        refresh = ui_el.refresh
        @wraps(refresh)
        def wrapper():
            if self.is_clear_refresh.isSet():
                # This refresh is internal and done to remove the label
                self.is_clear_refresh.clear()
            else:
                # This is the usual refresh - making sure we draw the label again
                self.active = True
                self.counter = 0
            return refresh()
        ui_el.refresh = wrapper

    def modify_image_if_needed(self, ui_el, image):
        if not self.active:
            return image
        c = Canvas(ui_el.o, base_image=image)
        self.draw_text(c, ui_el)
        image = c.get_image()
        return image

    def get_text_position(self, c, ui_el, text):
        pointer = ui_el.pointer
        fde = ui_el.view.first_displayed_entry
        position = pointer-fde
        entries_per_screen = ui_el.view.get_entry_count_per_screen()
        text_bounds = c.get_text_bounds(text, font=self.font)
        # Calculating offset from left screen edge to the clear coord start
        left_offset = max(0, c.width/2-text_bounds[0])
        # GridMenu-specific calculations for the left offset
        entry_width = getattr(ui_el.view, "entry_width", 0)
        if entry_width is None: entry_width = 0
        cols = getattr(ui_el, "cols", 0)
        if entry_width*cols > 0:
            left_offset = (entry_width*cols)/2 - text_bounds[0]/2
            left_offset = max(0, left_offset)
        # Generic calculations again
        # Calculating whether the label is show at the top or the bottom
        if position / float(entries_per_screen) > 0.5:
            # label at the top
            clear_coords = (left_offset, 0, text_bounds[0]+left_offset, text_bounds[1])
        else:
            # label at the bottom
            clear_coords = (left_offset, c.height-text_bounds[1]-self.text_border, text_bounds[0]+left_offset, c.height-1)
        text_coords = (clear_coords[0] + self.text_border, clear_coords[1] + self.text_border)
        return text_coords, clear_coords

    def draw_text(self, c, ui_el):
        entry_text = self.get_current_entry_text(ui_el)
        text_coords, clear_coords = self.get_text_position(c, ui_el, entry_text)
        c.clear(clear_coords)
        c.text(entry_text, text_coords, font=self.font)
