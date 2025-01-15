from functools import wraps
from threading import Event

from PIL import Image
Image = Image.Image

from ui.scrollable_element import TextReader
from ui.canvas import Canvas, expand_coords
from ui.utils import Rect, clamp
from ui.entry import Entry
from zpui_lib.helpers import get_all_available_keys

# Shorter code
# from https://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute/5021467#5021467
class AttrDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

class BaseOverlay(object):
    # Idea: an overlay could be applied to multiple UI elements
    # Implementation: all UI-element-specific data is stored by the UI element name
    # Requirement: unique UI element names ;,-(
    def __init__(self):
        self.uie = {} # Stores AttrDict for each UI element to which the overlay is applied

    def apply_to(self, ui_el):
        n = ui_el.name
        self.uie[n] = AttrDict()
        ui_el.overlays.append(self)

class BaseOverlayWithState(BaseOverlay):

    def __init__(self, duration = 20):
        BaseOverlay.__init__(self)

    def apply_to(self, ui_el):
        BaseOverlay.apply_to(self, ui_el)
        n = ui_el.name
        self.uie[n].active = Event()
        self.uie[n].active.clear()

    def set_state(self, ui_el, new_state):
        n = ui_el.name
        self.uie[n].active.set() if new_state else self.uie[n].active.clear()

    def get_state(self, ui_el):
        n = ui_el.name
        return self.uie[n].active.isSet()

class BaseOverlayWithTimeout(BaseOverlayWithState):

    def __init__(self, duration = 20):
        BaseOverlayWithState.__init__(self)
        self.duration = duration

    def apply_to(self, ui_el):
        BaseOverlayWithState.apply_to(self, ui_el)
        n = ui_el.name
        self.uie[n].counter = 0
        self.wrap_before_foreground(ui_el)
        self.wrap_idle_loop(ui_el)

    def update_state(self, ui_el):
        n = ui_el.name
        if self.uie[n].active.isSet():
            self.uie[n].counter += 1
            if self.uie[n].counter == self.duration:
                self.uie[n].active.clear()
                ui_el.refresh()

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
        n = ui_el.name
        @wraps(before_foreground)
        def wrapper(*args, **kwargs):
            return_value = before_foreground(*args, **kwargs)
            self.uie[n].active.set()
            self.uie[n].counter = 0
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

    def __init__(self, callback, key = "KEY_F5", wrap_view=True, **kwargs):
        self.callbacks = [callback]
        self.key = key
        self.do_wrap_view = wrap_view
        BaseOverlayWithTimeout.__init__(self, **kwargs)

    def apply_to(self, ui_el):
        self.wrap_generate_keymap(ui_el)
        if self.do_wrap_view:
            self.wrap_view(ui_el)
        BaseOverlayWithTimeout.apply_to(self, ui_el)

    def wrap_generate_keymap(self, ui_el):
        generate_keymap = ui_el.generate_keymap
        @wraps(generate_keymap)
        def wrapper(*args, **kwargs):
            keymap = generate_keymap(*args, **kwargs)
            key, callback = self.get_key_and_callback()
            if isinstance(callback, basestring):
                text = callback
                callback = TextReader(text, ui_el.i, ui_el.o, h_scroll=False).activate
            keymap[key] = ui_el.process_callback(callback)
            return keymap
        ui_el.generate_keymap = wrapper
        ui_el.set_default_keymap()

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

    def get_key_and_callback(self):
        return self.key, self.callbacks[-1]

    def modify_image_if_needed(self, ui_el, image):
        n = ui_el.name
        if self.uie[n].active.isSet():
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

    def __init__(self, keymap, labels=["Exit", "Options"], wrap_view=True, **kwargs):
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
        self.do_wrap_view = wrap_view
        BaseOverlayWithTimeout.__init__(self, **kwargs)

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
        half_line_length = c.o.cols//self.num_keys
        last_line = "".join([label.center(half_line_length) for label in self.labels])
        c.clear((self.right_offset, str(-self.bottom_offset), c.width-self.right_offset, c.height))
        c.text(last_line, (self.right_offset, str(-self.bottom_offset)), font=self.font)


class GridMenuSidebarOverlay(BaseOverlay):

    def __init__(self, sidebar_cb, top_o = None, bottom_o = None, left_o = None, right_o = None):
        BaseOverlay.__init__(self)
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

    def get_current_entry_text(self, ui_el):
        contents = ui_el.get_displayed_contents()
        entry = contents[ui_el.pointer]
        if isinstance(entry, Entry):
            return entry.text
        else:
            return entry[0]

    def apply_to(self, ui_el):
        BaseOverlay.apply_to(self, ui_el)
        n = ui_el.name
        self.uie[n].active = Event()
        self.uie[n].active.clear()
        self.uie[n].is_clear_refresh = Event()
        self.uie[n].last_pointer = 0
        self.uie[n].was_on_top = True
        self.wrap_view(ui_el)
        self.wrap_refresh(ui_el)
        self.wrap_idle_loop(ui_el)

    def update_state(self, ui_el):
        n = ui_el.name
        if self.uie[n].active.isSet():
            self.uie[n].counter += 1
            if self.uie[n].counter == self.duration:
                self.uie[n].active.clear()
                self.uie[n].is_clear_refresh.set()
                ui_el.refresh()

    def wrap_view(self, ui_el):
        def wrapper(image):
            if isinstance(image, Image):
                image = self.modify_image_if_needed(ui_el, image)
            return image
        ui_el.add_view_wrapper(wrapper)

    def wrap_refresh(self, ui_el):
        refresh = ui_el.refresh
        n = ui_el.name
        @wraps(refresh)
        def wrapper():
            if self.uie[n].is_clear_refresh.isSet():
                # This refresh is internal and done to remove the label
                self.uie[n].is_clear_refresh.clear()
            else:
                # This is the usual refresh - making sure we draw the label again
                self.uie[n].active.set()
                self.uie[n].counter = 0
            return refresh()
        ui_el.refresh = wrapper

    def modify_image_if_needed(self, ui_el, image):
        n = ui_el.name
        if not self.uie[n].active.isSet():
            return image
        c = Canvas(ui_el.o, base_image=image)
        self.draw_text(c, ui_el)
        image = c.get_image()
        return image

    def get_text_position(self, c, ui_el, text):
        n = ui_el.name
        pointer = ui_el.pointer
        fde = ui_el.view.first_displayed_entry
        position = pointer-fde
        entries_per_screen = ui_el.view.get_entry_count_per_screen()
        grid_rows = ui_el.rows
        text_bounds = c.get_text_bounds(text, font=self.font)
        # Calculating offset from left screen edge to the clear coord start
        left_offset = max(0, c.width//2-text_bounds[0])
        # GridMenu-specific calculations for the left offset
        entry_width = getattr(ui_el.view, "entry_width", 0)
        if entry_width is None: entry_width = 0
        cols = getattr(ui_el, "cols", 0)
        if entry_width*cols > 0:
            left_offset = (entry_width*cols)//2 - text_bounds[0]//2
            left_offset = max(0, left_offset)
        # Generic calculations again
        # Calculating whether the label is show at the top or the bottom
        text_y_offset = 0
        top_clear_coords = (left_offset, 0, text_bounds[0]+left_offset, text_bounds[1])
        bottom_clear_coords = (left_offset, c.height-text_bounds[1]-self.text_border, text_bounds[0]+left_offset, c.height-1)
        last_row_start = (ui_el.rows-1)*ui_el.cols
        top_bottom_entries = list(range(ui_el.cols)) + list(range(last_row_start, last_row_start+ui_el.cols))
        if grid_rows > 2 and position not in top_bottom_entries:
            if pointer == self.uie[n].last_pointer:
                clear_coords = top_clear_coords if self.uie[n].was_on_top else bottom_clear_coords
            else:
                if pointer > self.uie[n].last_pointer:
                    clear_coords = top_clear_coords
                    self.uie[n].was_on_top = True
                else:
                    self.uie[n].was_on_top = False
                    clear_coords = bottom_clear_coords
        elif position / float(entries_per_screen) > 0.5:
            # label at the top
            text_y_offset = -3
            clear_coords = top_clear_coords
            self.uie[n].was_on_top = True
        else:
            # label at the bottom
            clear_coords = bottom_clear_coords
            self.uie[n].was_on_top = False
        text_coords = (clear_coords[0] + self.text_border, clear_coords[1] + self.text_border + text_y_offset)
        self.uie[n].last_pointer = pointer
        return text_coords, clear_coords

    def draw_text(self, c, ui_el):
        entry_text = self.get_current_entry_text(ui_el)
        text_coords, clear_coords = self.get_text_position(c, ui_el, entry_text)
        entry_width = getattr(ui_el.view, "entry_width", 32)
        if entry_width is None: entry_width = 32
        clear_coords = (0, clear_coords[1], entry_width*ui_el.cols, clear_coords[3])
        c.clear(clear_coords)
        c.text(entry_text, text_coords, font=self.font)


class BaseNumpadOverlay(BaseOverlay):
    def __init__(self, default_cb, keys=None, callbacks=None):
        BaseOverlay.__init__(self)
        self.keys = list(range(10))+["*", "#"]
        if keys is not None:
            self.keys += keys
        self.callbacks = callbacks if callbacks is not None else {}
        self.default_callback = default_cb

    def get_callback_for_key(self, key):
        return self.callbacks.get(key, self.default_callback)

    def get_keymap(self, ui_el):
        keynames = ["KEY_{}".format(i) for i in self.keys]
        d = {}
        for name in keynames:
            cb_fun = self.get_callback_for_key(name)
            cb = lambda x=name: cb_fun(ui_el, x)
            d[name] = cb
        return d

    def apply_to(self, ui_el):
        BaseOverlay.apply_to(self, ui_el)
        self.wrap_generate_keymap(ui_el)

    def wrap_generate_keymap(self, ui_el):
        generate_keymap = ui_el.generate_keymap
        @wraps(generate_keymap)
        def wrapper(*args, **kwargs):
            keymap = generate_keymap(*args, **kwargs)
            keymap.update(self.get_keymap(ui_el))
            return keymap
        ui_el.generate_keymap = wrapper
        # Apply the changes
        ui_el.set_default_keymap()
        # apply_to is usually called after the UI element's __init__
        # has executed, so we need to call set_default_keymap once again


class GridMenuNavOverlay(BaseNumpadOverlay):
    def __init__(self, go_instantly=True, keys=None, callbacks=None):
        self.go_instantly = go_instantly
        self.nav_order = self.get_nav_order()
        BaseNumpadOverlay.__init__(self, lambda *a: True, keys=keys, callbacks=callbacks)

    def get_callback_for_key(self, key):
        return self.move_on_key

    def get_nav_order(self):
        nav_order_str = "123456789*0#"
        nav_order = ["KEY_{}".format(k) for k in nav_order_str]
        return nav_order

    def move_on_key(self, ui_el, key):
        if key not in self.nav_order:
            return # Weird, nav order does not contain a key
        index = self.nav_order.index(key)
        if ui_el.pointer == index or self.go_instantly:
            if self.go_instantly:
                ui_el.pointer = clamp(index, 0, len(ui_el.contents) - 1)
            # Moving to the same item that's already selected
            # let's interpret this as KEY_ENTER
            ui_el.select_entry(bypass_to_be_foreground=True)
            return
        ui_el.pointer = clamp(index, 0, len(ui_el.contents) - 1)
        ui_el.refresh()


class IntegerAdjustInputOverlay(BaseNumpadOverlay):
    def __init__(self):
        BaseNumpadOverlay.__init__(self, self.process_numpad_input, keys=None, callbacks=None)
        self.keys = list(range(10))
        self.input_order = {"KEY_{}".format(i):i for i in range(10)}

    def apply_to(self, ui_el):
        BaseNumpadOverlay.apply_to(self, ui_el)
        n = ui_el.name
        self.uie[n].numpad_input_has_started = Event()

    def process_numpad_input(self, ui_el, key):
        if key not in self.input_order:
            return # Weird, nav order does not contain a key
        digit = self.input_order[key]
        n = ui_el.name
        if self.uie[n].numpad_input_has_started.isSet():
            if ui_el.number is not None:
                number_str = str(ui_el.number)
                number_str += str(digit)
                ui_el.number = int(number_str)
            else:
                ui_el.number = digit
        else:
            self.uie[n].numpad_input_has_started.set()
            ui_el.number = digit
        ui_el.clamp()
        ui_el.refresh(bypass_to_be_foreground=True)


class SpinnerOverlay(BaseOverlayWithState):
    """
    A screen overlay that hooks onto an UI element, allowing you to show that some activity
    is happening in the background. Tailored for showing "Scanning" in the WiFi menu,
    should probably be put in that code, too. Shows a letter inside the spinner if ``letter``
    is set.
    """
    # TODO: an explicit ui_el.refresh after set_state(ui_el, False)
    # to clean up the spinner's remains?
    top_offset = 2
    right_offset = 15
    spinner_height = 8
    spinner_width = 7
    clear_margin = 2
    text_x_offset = 1
    text_y_offset = -2
    letter = "s"

    def __init__(self, wrap_view=True, **kwargs):
        self.do_wrap_view = wrap_view
        BaseOverlayWithState.__init__(self, **kwargs)

    def generate_coords(self, screen_width):
        o = screen_width - self.right_offset - self.spinner_width
        t = self.top_offset
        x = self.spinner_width
        y = self.spinner_height
        c = self.clear_margin
        self.coords = [ (o,   t,   o+x, t),
                        (o+x, t,   o+x, t+y),
                        (o,   t+y, o+x, t+y),
                        (o,   t,   o,   t+y)]
        self.text_coords = (o+self.text_x_offset, t+self.text_y_offset)
        self.clear_coords = (o-c, t-c, o+x+c, t+y+c)

    def apply_to(self, ui_el):
        BaseOverlayWithState.apply_to(self, ui_el)
        self.generate_coords(ui_el.o.width)
        if self.do_wrap_view:
            self.wrap_view(ui_el)
        self.wrap_idle_loop(ui_el)
        n = ui_el.name
        self.uie[n].spinner_stage = 0

    def wrap_view(self, ui_el):
        def wrapper(image):
            if isinstance(image, Image):
                image = self.modify_image_if_needed(ui_el, image)
            return image
        ui_el.add_view_wrapper(wrapper)

    def modify_image_if_needed(self, ui_el, image):
        n = ui_el.name
        if not self.uie[n].active.isSet():
            return image
        if self.uie[n].spinner_stage == 3:
            self.uie[n].spinner_stage = 0
        else:
            self.uie[n].spinner_stage += 1
        c = Canvas(ui_el.o, base_image=image)
        self.draw_spinner(c, self.uie[n].spinner_stage)
        image = c.get_image()
        return image

    def wrap_idle_loop(self, ui_el):
        idle_loop = ui_el.idle_loop
        n = ui_el.name
        @wraps(idle_loop)
        def wrapper(*args, **kwargs):
            return_value = idle_loop(*args, **kwargs)
            if self.uie[n].active.isSet():
                ui_el.refresh()
            return return_value
        ui_el.idle_loop = wrapper

    def draw_spinner(self, c, stage):
        c.clear(self.clear_coords)
        if self.letter:
            c.text(self.letter, self.text_coords)
        c.line(self.coords[stage])


class PurposeOverlay(BaseOverlayWithState):
    """
    An overlay that appears when the UI element is activated, shows
    the UI element's purpose (say, "Now choose timezone") and disappears
    on any key.
    """

    def __init__(self, purpose="Test"):
        BaseOverlayWithState.__init__(self)
        self.purpose = purpose

    def apply_to(self, ui_el):
        BaseOverlayWithState.apply_to(self, ui_el)
        n = ui_el.name
        self.wrap_generate_keymap(ui_el)
        self.wrap_before_activate(ui_el)
        self.wrap_view(ui_el)

    def wrap_before_activate(self, ui_el):
        before_activate = ui_el.before_activate
        n = ui_el.name
        @wraps(before_activate)
        def wrapper(*args, **kwargs):
            return_value = before_activate(*args, **kwargs)
            self.uie[n].active.set()
            return return_value
        ui_el.before_activate = wrapper

    def wrap_view(self, ui_el):
        def wrapper(image):
            if isinstance(image, Image):
                image = self.modify_image_if_needed(ui_el, image)
            return image
        ui_el.add_view_wrapper(wrapper)

    def wrap_generate_keymap(self, ui_el):
        generate_keymap = ui_el.generate_keymap
        n = ui_el.name
        @wraps(generate_keymap)
        def wrapper(*args, **kwargs):
            keymap = generate_keymap(*args, **kwargs)
            self.uie[n].keymap = keymap
            self.uie[n].generate_keymap = generate_keymap
            keys = get_all_available_keys(ui_el.i)
            f = lambda:self.deactivate_overlay(ui_el)
            new_keymap = {key:f for key in keys}
            return new_keymap
        ui_el.generate_keymap = wrapper
        ui_el.set_default_keymap()

    def deactivate_overlay(self, ui_el):
        n = ui_el.name
        self.uie[n].active.clear()
        ui_el.generate_keymap = self.uie[n].generate_keymap
        ui_el.set_keymap(self.uie[n].keymap)
        ui_el.refresh(bypass_to_be_foreground=True)

    def modify_image_if_needed(self, ui_el, image):
        n = ui_el.name
        if not self.uie[n].active.isSet():
            return image
        c = Canvas(ui_el.o, base_image=image)
        self.show_purpose(c)
        image = c.get_image()
        return image

    def show_purpose(self, c):
        bounds = c.get_centered_text_bounds(self.purpose)
        clear_coords = expand_coords(bounds, 3)
        c.clear(clear_coords)
        c.centered_text(self.purpose)
