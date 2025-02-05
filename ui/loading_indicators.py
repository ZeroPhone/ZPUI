import math
from math import cos
from threading import Thread
from time import time

from ui.canvas import Canvas
from ui.refresher import Refresher
from ui.utils import clamp, Chronometer, to_be_foreground, Rect
from helpers import setup_logger

"""
These UI elements are used to show the user that something is happening in the background.

There are two types of loading indicator elements:

1. "ProgressBar" elements, for when you can measure the progress that's made and remaining
2. "Loading" elements, for when you can't measure the progress, but have to show that a task is running in background

These classes are based on `Refresher`.
"""

# ========================= abstract classes =========================

logger = setup_logger(__name__, "info")


class Paused(object):
    """Wrapping for a `paused` context manager for loading indicators. Allows for:

    with li.paused:
        do some stuff
    """
    def __init__(self, obj):
        self.obj = obj

    def __enter__(self):
        self.obj.pause()
        return self

    def __exit__(self, *args):
        self.obj.resume()


class BaseLoadingIndicator(Refresher):
    """Abstract class for "loading indicator" elements."""
    on_left_cb = None

    def __init__(self, i, o, on_left=None, *args, **kwargs):
        self._progress = 0
        if on_left:
            self.set_on_left(on_left)
        keymap = kwargs.get("keymap", {})
        if "KEY_LEFT" not in keymap:
            keymap["KEY_LEFT"] = "on_left"
        kwargs["keymap"] = keymap
        Refresher.__init__(self, self.on_refresh, i, o, *args, **kwargs)
        self.t = None
        self.paused = Paused(self)

    def set_on_left(self, on_left):
        self.on_left_cb = on_left

    def on_refresh(self):
        pass

    def on_left(self):
        if callable(self.on_left_cb):
            self.on_left_cb()
        else:
            logger.warning("{}: User pressed LEFT but there's no LEFT handler, bad UX!".format(self.name))

    def set_message(self, new_message):
        self.message = new_message
        self.refresh()

    def run_in_background(self):
        if self.t is not None or self.is_active:
            raise Exception("BaseLoadingIndicator already running!")
        self.t = Thread(target=self.activate, name="Background thread for LoadingIndicator {}".format(self.name))
        self.t.daemon = True
        self.t.start()

    def stop(self):
        self.deactivate()
        self.t = None

    def __enter__(self):
        self.run_in_background()
        self.wait_for_active()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class ProgressIndicator(BaseLoadingIndicator):
    """Abstract class for "loading indicator" elements where the progress can be measured.
    Subclasses of ProgressIndicator, therefore, indicate a percentage of the progress
    that was done and is left."""

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = clamp(value, 0, 100)
        self.refresh()


# ========================= concrete classes =========================

class Throbber(BaseLoadingIndicator):
    """A throbber is a circular BaseLoadingIndicator, similar to those used on websites
    or in smartphones. Suitable for graphical displays and looks great on them!"""

    def __init__(self, i, o, *args, **kwargs):
        self._current_angle = 0
        self._current_range = 0  # range or width of the throbber
        self.rotation_speed = 360  # degree per second
        # We use a counter to make the rotation speed independent of the refresh-rate
        self.counter = Chronometer()
        self.start_time = 0
        self.message = kwargs.pop("message", None)
        BaseLoadingIndicator.__init__(self, i, o, refresh_interval=0.01, *args, **kwargs)

    def before_activate(self):
        self.start_time = time()
        self.counter.start()

    @to_be_foreground
    def refresh(self):
        self.update_throbber_angle()
        c = Canvas(self.o)
        self.draw_throbber(c)
        if self.message:
            self.draw_message(c)
        self.o.display_image(c.get_image())

    def draw_message(self, c):
        # type: (Canvas) -> None
        bounds = c.get_centered_text_bounds(self.message)
        # Drawn top-centered
        c.text(self.message, (bounds.left, 0), fill=True)

    def draw_throbber(self, c):
        x, y = c.size
        radius = min(x, y) / 4
        c.arc(
            (
                x / 2 - radius, y / 2 - radius,
                x / 2 + 1 + radius, y / 2 + radius
            ),
            start=(self._current_angle - self._current_range / 2) % 360,
            end=(self._current_angle + self._current_range / 2) % 360,
            fill=True
        )

    def update_throbber_angle(self):
        self.counter.update()
        self._current_angle += self.rotation_speed * self.counter.elapsed
        time_since_activation = time() - self.start_time
        self._current_range = cos(time_since_activation * math.pi) / 2 + 0.5
        self._current_range = (self._current_range * 170) + 10
        self.counter.restart()


class IdleDottedMessage(BaseLoadingIndicator):
    """ A simple (text-based) loading indicator, using three dots
    that are appearing and disappearing.
    Shows a message to the user."""

    def __init__(self, i, o, *args, **kwargs):
        BaseLoadingIndicator.__init__(self, i, o, *args, **kwargs)
        self.message = kwargs.pop("message", "Loading".center(o.cols).rstrip())
        self.dot_count = 0

    def on_refresh(self):
        BaseLoadingIndicator.on_refresh(self)
        self.dot_count = (self.dot_count + 1) % 4
        return self.message + '.' * self.dot_count


class CircularProgressBar(ProgressIndicator):
    """CircularProgressBar is half Throbber, half ProgressBar.
    Makes your app look all sci-fi!

    A circular progress bar for graphical displays.
    Allows to show or hide the progress percentage."""

    def __init__(self, i, o, *args, **kwargs):
        self.show_percentage = kwargs.pop("show_percentage", True)
        BaseLoadingIndicator.__init__(self, i, o, *args, **kwargs)

    def refresh(self):
        c = Canvas(self.o)
        x, y = c.size
        radius = min(x, y) / 4
        center_coordinates = (x / 2 - radius, y / 2 - radius, x / 2 + radius, y / 2 + radius)
        c.arc(center_coordinates, start=0, end=360 * (self.progress / 100.0), fill=True)
        if self.show_percentage:
            c.centered_text(str(self.progress)+"%")

        self.o.display_image(c.get_image())


class TextProgressBar(ProgressIndicator):
    """A horizontal progress bar for character-based displays, showing a message to the user.

    Allows to adjust characters used for drawing and the percentage field offset,
    as well as to show or hide the progress percentage."""

    def __init__(self, i, o, *args, **kwargs):
        # We need to pop() these arguments instead of using kwargs.get() because they
        # have to be removed from kwargs to prevent TypeErrors
        self.message = kwargs.pop("message", "Loading")
        self.fill_char = kwargs.pop("fill_char", "=")
        self.empty_char = kwargs.pop("empty_char", " ")
        self.border_chars = kwargs.pop("border_chars", "[]")
        self.show_percentage = kwargs.pop("show_percentage", False)
        self.percentage_offset = kwargs.pop("percentage_offset", 4)
        BaseLoadingIndicator.__init__(self, i, o, *args, **kwargs)
        self._progress = 0  # 0-100 range

    def set_message(self, new_message):
        self.message = new_message
        self.refresh()

    def get_progress_percentage(self):
        return '{}%'.format(self.progress)

    def get_bar_str(self, size):
        size -= len(self.border_chars)  # to let room for the border chars and/or percentage string
        bar_end = self.border_chars[1]
        if self.show_percentage:
            percentage = self.get_progress_percentage()
            # Leaving room for the border chars and/or percentage string
            size -= self.percentage_offset if self.percentage_offset > 0 else len(percentage)
            bar_end += percentage.rjust(self.percentage_offset)

        filled_col_count = int(size * (self.progress / 100.0))
        unfilled_col_count = size - filled_col_count
        fill_str = self.fill_char * int(filled_col_count) + self.empty_char * int(unfilled_col_count)

        bar = '{s}{bar}{e}'.format(
            bar=fill_str,
            s=self.border_chars[0],
            e=bar_end
        )
        return bar

    def on_refresh(self):
        BaseLoadingIndicator.on_refresh(self)
        bar = self.get_bar_str(self.o.cols)
        return [self.message.center(self.o.cols), bar]


class GraphicalProgressBar(ProgressIndicator):
    """ A horizontal progress bar for graphical displays, showing a message to the user.
    Allows to adjust padding and margin for a little bit of customization,
    as well as to show or hide the progress percentage."""

    def __init__(self, i, o, *args, **kwargs):
        self.message = kwargs.pop("message", "Loading")
        self.show_percentage = kwargs.pop("show_percentage", True)
        self.margin = int(kwargs.pop("margin", 7))
        self.text_margin = int(kwargs.pop("text_margin", 0))
        self.percentage_margin = int(kwargs.pop("percentage_margin", 40))
        self.padding = int(kwargs.pop("padding", 2))
        self.bar_height = kwargs.pop("bar_height", 15)
        BaseLoadingIndicator.__init__(self, i, o, *args, **kwargs)

    def refresh(self):
        c = Canvas(self.o)
        if self.show_percentage:
            percentage_text = "{}%".format(self.progress)
            coords = c.get_centered_text_bounds(percentage_text)
            c.text(percentage_text, (coords.left, self.percentage_margin), fill=True)  # Drawn top-centered (with margin)
            bar_top_min = self.margin + (coords.bottom - coords.top)
            bar_top = bar_top_min if self.margin < bar_top_min else self.margin
        else:
            bar_top = self.o.width / 2

        self.draw_message(c)
        self.draw_bar(c, bar_top)

        self.o.display_image(c.get_image())

    def draw_message(self, c):
        # type: Canvas -> None
        coords = c.get_centered_text_bounds(self.message)
        c.text(self.message, (coords.left, self.text_margin))

    def draw_bar(self, c, top_y):
        # type: (Canvas, int) -> None
        outline_coords = Rect(
            self.margin,
            top_y,
            self.o.width - self.margin,
            min(top_y + self.bar_height, self.o.height - self.margin)
        )

        bar_width = outline_coords.right - outline_coords.left - self.padding * 2
        bar_width *= (self.progress / 100.0)

        bar_coords = Rect(
            outline_coords.left + self.padding,
            outline_coords.top + self.padding,
            outline_coords.left + self.padding + int(bar_width),
            outline_coords.bottom - self.padding
        )

        c.rectangle(outline_coords, fill=False, outline=True)
        c.rectangle(bar_coords, fill=True, outline=False)


# noinspection PyPep8Naming
def ProgressBar(i, o, *args, **kwargs):
    """Instantiates and returns the appropriate kind of progress bar
    for the output device - either graphical or text-based."""
    if "b&w" in o.type:
        return GraphicalProgressBar(i, o, *args, **kwargs)
    elif "char" in o.type:
        return TextProgressBar(i, o, *args, **kwargs)
    else:
        raise ValueError("Unsupported display type: {}".format(repr(o.type)))

# noinspection PyPep8Naming
def LoadingBar(i, o, *args, **kwargs):
    """Instantiates and returns the appropriate kind of loading indicator
    for the output device - either graphical or text-based."""
    if "b&w" in o.type:
        return Throbber(i, o, *args, **kwargs)
    elif "char" in o.type:
        return IdleDottedMessage(i, o, *args, **kwargs)
    else:
        raise ValueError("Unsupported display type: {}".format(repr(o.type)))
