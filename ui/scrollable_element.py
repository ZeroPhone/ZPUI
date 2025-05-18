from __future__ import division

from textwrap import wrap
from time import sleep, time

from ui.canvas import Canvas, get_default_font
from ui.funcs import format_for_screen
from ui.utils import to_be_foreground, clamp
from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "warning")


class VerticalScrollbar(object):
    def __init__(self, o, width=1, min_size=1, margin=1, color="white"):
        self.o = o
        self._width = width
        self.margin = margin
        self.min_size = min_size
        self.color = color
        self._progress = 0  # 0-1 range, 0 is top, 1 is bottom
        self.size = 0  # 0-1 range, 0 is minimum size, 1 is whole screen

    def is_visible(self):
        return True

    def draw(self, c, forced=True):
        # type: (Canvas) -> None
        rect = self.get_coords(c)
        c.rectangle(rect, fill=self.color)

    def get_coords(self, c):
        height_px = c.height * self.size
        height_px = max(height_px, self.min_size)  # so we always have something to show
        y_pos = int(self.progress * c.height)
        rect = (
            self.margin, y_pos,
            self.margin + self._width, y_pos + height_px
        )
        return rect

    @property
    def width(self):
        # Returns the total width, with margins
        return self.margin * 2 + self._width

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = clamp(value, 0, 1)


class HorizontalScrollbar(VerticalScrollbar):

    def get_coords(self, c):
        width_px = c.width * self.size
        width_px = max(width_px, self.min_size)
        x_pos = int(self.progress * c.width)
        rect = (
            x_pos, c.height - self._width - self.margin,
            x_pos + width_px, c.height - self.margin
        )
        return rect

    def draw(self, c, forced=True):
        rect = self.get_coords(c)
        c.rectangle(
            self.get_background_coords(c),
            fill="black",
            outline="black",
        )
        c.rectangle(rect, fill=self.color)

    def get_background_coords(self, c):
        return 0, c.height - self.width, c.width, c.height


class HideableVerticalScrollbar(VerticalScrollbar):

    scrollbar_color = "white"

    def __init__(self, o, width=1, min_size=1, margin=1, color="white", fade_time=1):
        self.update_color() # vestigial
        super(HideableVerticalScrollbar, self).__init__(o, width, min_size, margin, color)
        self.fade_time = fade_time
        self.last_activity = -fade_time

    def draw(self, c, forced=False):
        # type: (Canvas) -> None
        rect = self.get_coords(c)
        #self.update_color()
        if self.is_visible() or forced:
            c.rectangle(rect, fill=self.color, outline=self.color)
        return c

    def update_color(self):
        self.color = self.scrollbar_color
        # if self.is_visible() else False

    def is_visible(self):
        ret = time() < self.last_activity + self.fade_time
        return ret

    # noinspection PyMethodOverriding
    @VerticalScrollbar.progress.setter
    def progress(self, value):
        self.last_activity = time()
        if value == self.progress:
            return
        self._progress = clamp(value, 0, 1)


class HideableHorizontalScrollbar(HorizontalScrollbar, HideableVerticalScrollbar):

    def __init__(self, o, width=1, min_size=1, margin=1, color="white", fade_time=1):
        HorizontalScrollbar.__init__(self, o, width, min_size, margin, color)
        HideableVerticalScrollbar.__init__(self, o, width, min_size, margin, color, fade_time)

    def get_coords(self, c):
        return HorizontalScrollbar.get_coords(self, c)

    def draw(self, c, forced=False):
        #self.update_color()
        if self.is_visible() or forced:
            HorizontalScrollbar.draw(self, c)


class TextReader(object):
    """A vertical-scrollable ui element used to read text"""

    # todo : documentation
    def __init__(self, text, i, o, name="TextReader", sleep_interval=1, scroll_speed=2, autohide_scrollbars=True, fade_time=1,
                 h_scroll=None):
        self.i = i
        self.o = o
        self.text = text
        self.name = name
        self.sleep_interval = sleep_interval
        self.scroll_speed = scroll_speed
        self.keymap = dict
        self.h_scroll = h_scroll
        self.autohide_scrollbars = autohide_scrollbars

        if self.autohide_scrollbars:
            self.v_scrollbar = HideableVerticalScrollbar(self.o, margin=2, fade_time=fade_time)
            self.h_scrollbar = HideableHorizontalScrollbar(self.o, margin=2, fade_time=fade_time)
        else:
            self.v_scrollbar = VerticalScrollbar(self.o)
            self.h_scrollbar = HorizontalScrollbar(self.o)

        self.calculate_params()

        self.in_foreground = False
        self.v_scroll_index = 0
        self.h_scroll_index = 0

        self.after_move()

    def calculate_params(self):
        if self.o.width < 240:
            self.font = get_default_font()
            self.char_height = self.o.char_height
            self.char_width = self.o.char_width
            self.cols = self.o.cols
            self.rows = self.o.rows
        else:
            self.char_height = 16
            self.char_width = 8
            self.font = ("Fixedsys62.ttf", self.char_height)
            self.cols = self.o.width // self.char_width
            self.rows = self.o.height // self.char_height

        text_width = (self.o.width - self.v_scrollbar.width) // self.char_width

        self._content = self.text.splitlines() if self.h_scroll else format_for_screen(self.text, text_width)
        self._content_width = max([len(line) for line in self._content])
        self.horizontal_scroll = self.h_scroll if self.h_scroll is not None else self._content_width > self.cols
        self._content_height = len(self._content)

    def activate(self):
        logger.info("{0} activated".format(self.name))
        self.to_foreground()
        while self.in_foreground:  # All the work is done in input callbacks
            self.idle_loop()
            self.check_for_scrollbarhide()
        logger.info("{} exited".format(self.name))
        return None

    def idle_loop(self):
        sleep(self.sleep_interval)

    def check_for_scrollbarhide(self):
        if self.autohide_scrollbars:
            scrollbar_active = self.v_scrollbar.is_visible() or self.h_scrollbar.is_visible()
            if not scrollbar_active and self.scrollbar_active:
                logger.debug("{}: scrollbars get hidden".format(self.name))
                self.refresh(auto_refresh=True)  # needed to update the hideable scrollbars
                self.scrollbar_active = scrollbar_active

    @to_be_foreground
    def refresh(self, auto_refresh = False):
        text = self.get_displayed_text()
        c = Canvas(self.o)
        self.draw_text(text, c, self.v_scrollbar.width)
        self.v_scrollbar.draw(c, forced=not auto_refresh)
        self.h_scrollbar.draw(c, forced=not auto_refresh)
        self.o.display_image(c.get_image())
        if not auto_refresh: self.after_move() # refresh is generally called after a move; also, we need this to refresh the scrollbars

    def draw_text(self, text, c, x_offset):
        for line, arg in enumerate(text):
            y = (line * self.char_height)
            c.text(arg, (x_offset, y), font=self.font)

    def get_displayed_text(self):
        start = int(self.h_scroll_index)
        end = start + self.rows
        displayed_data = self._content[start:end]
        if self.horizontal_scroll:
            displayed_data = [line[self.v_scroll_index:self.cols + self.v_scroll_index] for line in displayed_data]

        return displayed_data

    @to_be_foreground
    def set_keymap(self):
        self.generate_keymap()
        self.i.stop_listen()
        self.i.set_keymap(self.keymap)
        self.i.listen()

    def generate_keymap(self):
        self.keymap = {
            "KEY_UP": lambda: self.move_up(),
            "KEY_DOWN": lambda: self.move_down(),
            "KEY_F3": lambda: self.page_up(),
            "KEY_F4": lambda: self.page_down(),
            "KEY_LEFT": lambda: self.move_left(),
            "KEY_RIGHT": lambda: self.move_right(),
            "KEY_ENTER": lambda: self.deactivate()
        }

    def to_foreground(self):
        logger.info("{0} enabled".format(self.name))
        self.in_foreground = True
        self.refresh()
        self.set_keymap()

    def deactivate(self):
        self.in_foreground = False

    def move_up(self):
        self.h_scroll_index -= self.scroll_speed
        self.refresh()

    def move_down(self):
        self.h_scroll_index += self.scroll_speed
        self.refresh()

    def move_right(self):
        self.v_scroll_index += self.scroll_speed
        self.refresh()

    def move_left(self):
        if self.v_scroll_index == 0:
            self.deactivate()

        self.v_scroll_index -= self.scroll_speed
        self.refresh()

    def page_up(self):
        self.h_scroll_index -= self.scroll_speed * 2
        self.refresh()

    def page_down(self):
        self.h_scroll_index += self.scroll_speed * 2
        self.refresh()

    def after_move(self):
        # the if-else sections try to account for "empty string" scenario
        self.v_scrollbar.size = self.rows // self._content_height if self._content_height else 1
        self.h_scrollbar.size = self.cols // self._content_width if self._content_width else 1
        self.h_scroll_index = clamp(self.h_scroll_index, 0, self._content_height - self.rows + 1)
        self.v_scroll_index = clamp(self.v_scroll_index, 0, self._content_width - self.cols + 1)
        self.v_scrollbar.progress = self.h_scroll_index / self._content_height if self._content_height else 0
        self.h_scrollbar.progress = self.v_scroll_index / self._content_width if self._content_width else 0
        self.scrollbar_active = True
