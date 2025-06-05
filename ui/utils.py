from collections import namedtuple
from collections.abc import Sequence
from functools import wraps
from time import time, sleep

from PIL import ImageOps, Image

from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "warning")


to_be_foreground_warnings = []

def to_be_foreground(func):
    """ A safety check wrapper so that certain functions can't possibly be called
    if UI element is not the one active"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        bypass = False
        if "bypass_to_be_foreground" in kwargs:
            if kwargs.pop("bypass_to_be_foreground"):
                bypass  = True
        if bypass or self.in_foreground:
            return func(self, *args, **kwargs)
        else:
            data = (self.__class__.__name__, func.__name__, getattr(self, "name", None))
            if data not in to_be_foreground_warnings:
                to_be_foreground_warnings.append(data)
                logger.warning("{}.{} (UI el {}) was prevented from being executed " \
                               "by to_be_foreground!".format(*data) )
            return False
    return wrapper


def clamp(value, _min, _max):
    """
    Returns a value clamped between two bounds (inclusive)
    >>> clamp(17, 0, 100)
    17
    >>> clamp(-89, 0, 100)
    0
    >>> clamp(65635, 0, 100)
    100
    """
    return max(_min, min(value, _max))


def is_sequence_not_string(value):
    """
    Checks if the value passed is a sequence, like a list or tuple - except strings.
    """
    return isinstance(value, Sequence) and not isinstance(value, basestring)


def modulo_list_index(value, _list):
    """
    Returns an always valid list index. Repeats the list circularly.
    >>> robots=['R2D2', 'C3PO', 'HAL9000']
    >>> robots[modulo_list_index(0, robots)]
    'R2D2'
    >>> robots[modulo_list_index(3, robots)]
    'R2D2'
    >>> [robots[modulo_list_index(i, robots)] for i in range(10)]
    ['R2D2', 'C3PO', 'HAL9000', 'R2D2', 'C3PO', 'HAL9000', 'R2D2', 'C3PO', 'HAL9000', 'R2D2']
    """
    return value % len(_list)


def clamp_list_index(value, _list):
    """
    Returns a list index clamped to the bounds of the list.
    Useful to prevent iterating out of bounds, repeats the bounds values.
    >>> astronauts = ['Collins', 'Armstrong', 'Aldrin']
    >>> astronauts[clamp_list_index(0, astronauts)]
    'Collins'
    >>> astronauts[clamp_list_index(2, astronauts)]
    'Aldrin'
    >>> astronauts[clamp_list_index(9000, astronauts)]
    'Aldrin'
    >>> astronauts[clamp_list_index(-666, astronauts)]
    'Collins'
    """
    return clamp(value, 0, len(_list) - 1)


def check_value_lock(func):
    """ A safety check wrapper so that there's no race conditions
    between functions that are able to change position/value"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        assert self.value_lock, "Class has no member self.value_lock"  # todo:maybe we should create it here ?
        # Value-changing code is likely to run in concurrent thread and therefore we need a lock
        if self.__locked_name__ is not None:
            logger.warning(
                "Another function already working with the value! Name is {}, current is {}".format(
                    self.__locked_name__,
                    func.__name__
                )
            )
        with self.value_lock:
            self.__locked_name__ = func.__name__
            logger.debug("Locked function {}".format(func.__name__))
            result = func(self, *args, **kwargs)
        logger.debug("Unlocked function {}".format(func.__name__))
        self.__locked_name__ = None
        return result

    return wrapper


class Chronometer(object):
    """
    This object measures time.
    >>> cron = Chronometer()
    >>> cron.active
    False
    >>> cron.start()
    >>> cron.active
    True
    >>> sleep(1)
    >>> cron.update()
    >>> round(cron.elapsed, 1)
    1.0
    >>> cron.pause()
    >>> sleep(1)
    >>> round(cron.elapsed, 1)
    1.0
    >>> cron.toggle()  # or cron.resume()
    >>> sleep(1)
    >>> cron.update()
    >>> round(cron.elapsed, 1)
    2.0
    >>> cron.restart()
    >>> sleep(1)
    >>> cron.update()
    >>> round(cron.elapsed, 1)
    1.0
    """
    def __init__(self):
        self.__active = False
        self.__cron = Ticker()
        self.__elapsed = 0

    @property
    def active(self):
        # type: () -> bool
        """whether the Chronometer is counting time"""
        return self.__active

    @property
    def elapsed(self):
        # type: () -> float
        """returns the elapsed time"""
        return self.__elapsed

    def update(self):
        # type: () -> None
        """Updates the chronometer with the current time"""
        if not self.__active:
            return
        self.__elapsed += self.__cron.tick()

    def stop(self):
        # type: () -> None
        """Stop and resets the Chronometer"""
        self.__cron.tick()
        self.__elapsed = 0
        self.__active = False

    def pause(self):
        # type: () -> None
        """Pauses the Chronometer, but keeps the measured time so far"""
        self.__active = False

    def resume(self):
        # type: () -> None
        """Resumes measuring time after a pause"""
        self.__cron.tick()
        self.__active = True

    def start(self):
        # type: () -> None
        """Starts measuring time"""
        self.stop()
        self.resume()

    def toggle(self):
        # type: () -> None
        """Toggles between pause and resume"""
        self.pause() if self.active else self.resume()

    def restart(self):
        # type: () -> None
        """Resets the Chronometer and starts a new measure immediatly"""
        self.start()


class Ticker(object):
    """
    This object returns the time elapsed between two calls to it's `tick()` function
    >>> ticker = Ticker()
    >>> sleep(1)
    >>> elapsed = ticker.tick()
    >>> round(elapsed, 1)  #rounded because time.sleep() is not that precise
    1.0
    """
    def __init__(self):
        self.__active = False
        self.__last_call = time()

    def tick(self):
        """
        :rtype: int
        :return: the time elapsed since the previous tick
        """
        now = time()
        elapsed = now - self.__last_call
        self.__last_call = now
        return elapsed


Rect = namedtuple('Rect', ['left', 'top', 'right', 'bottom'])

def fit_image_to_screen(image, o, resampling=Image.BOX, fill_color="black"):
    """Fits a given image to fit on any sized screen whilst maintaining the aspect ratio.
    Any remaining space is filled with borders. The resized image is returned as ``image``.

    Args:

        * ``image``: A PIL image to be resized.
        * ``o``: output device object. Used to find the width and height of the screen.
        * ``resampling=PIL.Image.BOX``: PIL resampling algorithm to be used during resizing.
        See https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-filters ."""
    return fit_image_to_dims(image, o.width, o.height, resampling=resampling, fill_color=fill_color)

def fit_image_to_dims(image, width, height, resampling=Image.BOX, fill_color = "black"):
    """Fits a given image to fit on any sized screen whilst maintaining the aspect ratio.
    Any remaining space is filled with borders. The resized image is returned as ``image``.

    Args:

        * ``image``: A PIL image to be resized.
        * ``width``: target width.
        * ``height``: target height.
        * ``resampling=PIL.Image.BOX``: PIL resampling algorithm to be used during resizing.
        See https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-filters ."""
    orig_image = image
    image_width, image_height = image.size
    if height > image_height and width > image.width: # Checks if the screen dimensions are equal to the image size
        logger.debug("Using resize script")
        if height/image_height < width/image_width: # Checks which side is bigger in proportion to the image size
            logger.debug("Using height as multiplier")
            bigger_side = height
            bigger_image_side = image_height
            smaller_image_side = image_width
        else:
            logger.debug("Using width as multiplier")
            bigger_side = width
            bigger_image_side = image_width
            smaller_image_side = image_height
        bigger_side_percent = (bigger_side/float(bigger_image_side))
        other_size = int((float(smaller_image_side)*float(bigger_side_percent))) # Working out smaller side length
        image = image.resize((bigger_side,other_size), resampling) # Resizes the image to the calculated dimensions to fit the screen and stick to the aspect ratio using a $
    elif (width, height) == image.size: # Checks if screen dimensions and exactly the same as image dimensions
        logger.debug("Exact same size - no changes needed")
    elif (width == image_width and height > image_height) or (height == image_height and width > image_width):
        logger.debug("One side is the same, the other is bigger - borders needed")
    else: # This should happen if the screen is smaller on one or both sides than the image
        logger.debug("Using thumbnail script")
        size = width, height
        image.thumbnail(size, resampling) # Resizes the image sticking to the aspect ratio using
    if (width, height) != image.size:
        logger.debug("Adding borders")
        left = top = right = bottom = 0
        iwidth, iheight = image.size
        if width > iwidth:
            logger.debug("Adding borders for width")
            delta = width - iwidth
            left = delta // 2
            right = delta - left
        if height > iheight:
            logger.debug("Adding borders for height")
            delta = height - iheight
            top = delta // 2
            bottom = delta - top
        image = ImageOps.expand(image, border=(left, top, right, bottom), fill=fill_color)
        logger.info("Borders added to image {} are: top - {}, bottom - {}, left - {} and right - {}".format(orig_image, top, bottom, left, right))
    logger.debug("All resizing finished")
    return image
