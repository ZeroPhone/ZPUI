from __future__ import division

import math
from collections import namedtuple
from math import cos
from threading import Thread
from time import time

from PIL import ImageDraw
from luma.core.render import canvas

from ui import Refresher
from ui.utils import clamp, Chronometer, to_be_foreground

"""These UI elements are used to show the user that something is happening in the background.

There are two types of loading indicator elements:

1. "ProgressBar" elements, for when you can measure the progress that's made and remaining
2. "Loading" elements, for when you can't measure the progress that's made and remaining

These classes are based on `Refresher`."""

# ========================= helpers =========================

Rect = namedtuple('Rect', ['left', 'top', 'right', 'bottom'])


class CenteredTextRenderer(object):
    # TODO: refactor into the ZPUI canvas wrapper that's bound to appear in the future.
    def draw_centered_text(self, draw, content, device_size):
        # type: (ImageDraw, str, tuple) -> None
        """Draws a centered text on the canvas and returns a 4-tuple of the coordinates taken by the text"""
        coords = self.get_centered_text_bounds(draw, content, device_size)
        draw.text((coords.left, coords.top), content, fill=True)

    @staticmethod
    def get_centered_text_bounds(draw, content, device_size):
        # type: (ImageDraw, str, tuple) -> Rect
        """Returns the coordinates of the centered text (min_x, min_y, max_x, max_y)"""
        w, h = draw.textsize(content)
        dw, dh = device_size
        return Rect(dw / 2 - w / 2, dh / 2 - h / 2, dw / 2 + w / 2, dh / 2 + h / 2)

    @staticmethod
    def get_center(device_size):
        # type: (tuple) -> tuple
        return device_size[0] / 2, device_size[1] / 2

# ========================= abstract classes =========================


class LoadingIndicator(Refresher):
    """Abstract class for "loading indicator" elements."""
    def __init__(self, i, o, *args, **kwargs):
        self._progress = 0
        Refresher.__init__(self, self.on_refresh, i, o, *args, **kwargs)
        self.t = None

    def on_refresh(self):
        pass

    def run_in_background(self):
        if self.t is not None or self.in_foreground:
            raise Exception("LoadingIndicator already running!")
        self.t = Thread(target=self.activate)
        self.t.daemon = True
        self.t.start()

    def stop(self):
        self.deactivate()
        self.t = None

    def __enter__(self):
        self.run_in_background()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

class ProgressIndicator(LoadingIndicator):
    """Abstract class for "loading indicator" elements where the progress can be measured.
    Subclasses of ProgressIndicator, therefore, indicate a percentage of the progress
    that was done and is left."""
    @property
    def progress(self):
        return float(self._progress)

    @progress.setter
    def progress(self, value):
        self._progress = clamp(value, 0, 1)
        self.refresh()


# ========================= concrete classes =========================

class Throbber(LoadingIndicator, CenteredTextRenderer):
    """A throbber is a circular LoadingIndicator, similar to those used on websites
    or in smartphones. Suitable for graphical displays and looks great on them!"""

    def __init__(self, i, o, *args, **kwargs):
        self._current_angle = 0
        self._current_range = 0  # range or width of the throbber
        self.rotation_speed = 360  # degree per second
        # We use a counter to make the rotation speed independent of the refresh-rate
        self.counter = Chronometer()
        self.start_time = 0
        self.message = kwargs.pop("message") if "message" in kwargs else None
        LoadingIndicator.__init__(self, i, o, refresh_interval=0.01, *args, **kwargs)

    def activate(self):
        self.start_time = time()
        self.counter.start()
        return Refresher.activate(self)

    @to_be_foreground
    def refresh(self):
        self.update_throbber_angle()
        c = canvas(self.o.device)
        c.__enter__()
        draw = c.draw
        self.draw_throbber(c, draw)
        if self.message:
            self.draw_message(draw)
        self.o.display_image(c.image)

    def draw_message(self, draw):
        # type: (ImageDraw) -> None
        bounds = self.get_centered_text_bounds(draw, self.message, self.o.device.size)

        draw.text((bounds.left, 0), self.message, fill=True)  # Drawn top-centered (with margin)

    def draw_throbber(self, c, draw):
        c.__enter__()
        x, y = c.device.size
        radius = min(x, y) / 4
        draw.arc(
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


class IdleDottedMessage(LoadingIndicator):
    """ A simple (text-based) loading indicator, using three dots
    that are appearing and disappearing.
    Shows a message to the user."""
    def __init__(self, i, o, *args, **kwargs):
        LoadingIndicator.__init__(self, i, o, *args, **kwargs)
        self.message = kwargs.pop("message") if "message" in kwargs else "Loading".center(o.cols).rstrip()
        self.dot_count = 0

    def on_refresh(self):
        LoadingIndicator.on_refresh(self)
        self.dot_count = (self.dot_count + 1) % 4
        return self.message + '.' * self.dot_count


class CircularProgressBar(ProgressIndicator, CenteredTextRenderer):
    """CircularProgressBar is half Throbber, half ProgressBar.
    Makes your app look all sci-fi!

    A circular progress bar for graphical displays.
    Allows to show or hide the progress percentage."""
    def __init__(self, i, o, *args, **kwargs):
        self.show_percentage = kwargs.pop("show_percentage") if "show_percentage" in kwargs else True
        LoadingIndicator.__init__(self, i, o, *args, **kwargs)

    def refresh(self):
        c = canvas(self.o.device)
        c.__enter__()
        x, y = c.device.size
        radius = min(x, y) / 4
        draw = c.draw
        center_coordinates = (x / 2 - radius, y / 2 - radius, x / 2 + radius, y / 2 + radius)
        draw.arc(center_coordinates, start=0, end=360 * self.progress, fill=True)
        if self.show_percentage:
            self.draw_centered_text(draw, "{:.0%}".format(self.progress), self.o.device.size)

        self.o.display_image(c.image)


class TextProgressBar(ProgressIndicator):
    """A horizontal progress bar for character-based displays, showing a message to the user.

    Allows to adjust characters used for drawing and the percentage field offset,
    as well as to show or hide the progress percentage."""
    def __init__(self, i, o, *args, **kwargs):
        # We need to pop() these arguments instead of using kwargs.get() because they
        # have to be removed from kwargs to prevent TypeErrors
        self.message = kwargs.pop("message") if "message" in kwargs else "Loading"
        self.fill_char = kwargs.pop("fill_char") if "fill_char" in kwargs else "="
        self.empty_char = kwargs.pop("empty_char") if "empty_char" in kwargs else " "
        self.border_chars = kwargs.pop("border_chars") if "border_chars" in kwargs else "[]"
        self.show_percentage = kwargs.pop("show_percentage") if "show_percentage" in kwargs else False
        self.percentage_offset = kwargs.pop("percentage_offset") if "percentage_offset" in kwargs else 4
        LoadingIndicator.__init__(self, i, o, *args, **kwargs)
        self._progress = 0  # 0-1 range

    def set_message(self, new_message):
        self.message = new_message
        self.refresh()

    def get_progress_percentage(self):
        return '{}%'.format(self.progress * 100)

    def get_progress_percentage_string(self):
        return '{}%'.format(int(self.progress * 100))

    def get_bar_str(self, size):
        size -= len(self.border_chars)  # to let room for the border chars and/or percentage string
        bar_end = self.border_chars[1]
        if self.show_percentage:
            percentage = self.get_progress_percentage_string()
            # Leaving room for the border chars and/or percentage string
            size -= self.percentage_offset if self.percentage_offset > 0 else len(percentage)
            bar_end += percentage.rjust(self.percentage_offset)

        filled_col_count = int(size * self.progress)
        unfilled_col_count = size - filled_col_count
        fill_str = self.fill_char * int(filled_col_count) + self.empty_char * int(unfilled_col_count)

        bar = '{s}{bar}{e}'.format(
            bar=fill_str,
            s=self.border_chars[0],
            e=bar_end
        )
        return bar

    def on_refresh(self):
        LoadingIndicator.on_refresh(self)
        bar = self.get_bar_str(self.o.cols)
        return [self.message.center(self.o.cols), bar]


class GraphicalProgressBar(ProgressIndicator, CenteredTextRenderer):
    """ A horizontal progress bar for graphical displays, showing a message to the user.
    Allows to adjust padding and margin for a little bit of customization,
    as well as to show or hide the progress percentage."""
    def __init__(self, i, o, *args, **kwargs):
        self.message = kwargs.pop("message") if "message" in kwargs else None
        self.show_percentage = kwargs.pop("show_percentage") if "show_percentage" in kwargs else True
        self.margin = kwargs.pop("margin") if "margin" in kwargs else 15
        self.padding = kwargs.pop("padding") if "padding" in kwargs else 2
        self.bar_height = kwargs.pop("bar_height") if "bar_height" in kwargs else 15
        LoadingIndicator.__init__(self, i, o, *args, **kwargs)

    def refresh(self):
        c = canvas(self.o.device)
        c.__enter__()
        draw = c.draw
        bar_top = self.o.device.size[1] / 2
        if self.show_percentage:
            percentage_text = "{:.0%}".format(self.progress)
            coords = self.get_centered_text_bounds(draw, percentage_text, self.o.device.size)
            draw.text((coords.left, self.margin), percentage_text, fill=True)  # Drawn top-centered (with margin)
            bar_top = self.margin + (coords.bottom - coords.top)

        self.draw_bar(draw, bar_top)

        if self.message:
            self.draw_message(draw)

        self.o.display_image(c.image)

    def draw_message(self, draw):
        # type: (ImageDraw) -> None
        bounds = self.get_centered_text_bounds(draw, self.message, self.o.device.size)

        draw.text((bounds.left, 0), self.message, fill=True)  # Drawn top-centered (with margin)

    def draw_bar(self, draw, top_y):
        # type: (ImageDraw, float) -> None
        width, height = self.o.device.size

        outline_coords = Rect(
            self.margin,
            top_y,
            width - self.margin,
            min(top_y + self.bar_height, height - self.margin)
        )

        bar_width = outline_coords.right - outline_coords.left - self.padding * 2
        bar_width *= self.progress

        bar_coords = Rect(
            outline_coords.left + self.padding,
            outline_coords.top + self.padding,
            outline_coords.left + self.padding + bar_width,
            outline_coords.bottom - self.padding
        )

        draw.rectangle(outline_coords, fill=False, outline=True)
        draw.rectangle(bar_coords, fill=True, outline=False)


def ProgressBar(i, o, *args, **kwargs):
    """Instantiates and returns the appropriate kind of progress bar
    for the output device - either graphical or text-based."""
    if not hasattr(o, "type"): # In case we're on an emulator...
        return GraphicalProgressBar(i, o, *args, **kwargs)
    if "b&w-pixel" in o.type:
        return GraphicalProgressBar(i, o, *args, **kwargs)
    elif "char" in o.type:
        return TextProgressBar(i, o, *args, **kwargs)
    else:
        raise ValueError("Unsupported display type: {}".format(repr(o.type)))
