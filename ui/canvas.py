import os

from PIL import Image, ImageDraw, ImageOps, ImageFont, ImageColor
import numpy as np

from ui.utils import is_sequence_not_string as issequence, Rect

fonts_dir = "ui/fonts/"
font_cache = {}

from zpui_lib.helpers import setup_logger
logger = setup_logger(__name__, "warning")

default_font = None
def get_default_font():
    global default_font
    if not default_font:
        logger.debug("Loading default font from the font storage directory")
        path = os.path.join(fonts_dir, 'courB08.pil')
        default_font = ImageFont.load(path)
    return default_font

class Canvas(object):
    """
    This object allows you to work with graphics on the display quicker and easier.
    You can draw text, graphical primitives, insert bitmaps and do other things
    that the ``PIL`` library allows, with a bunch of useful helper functions.

    Args:

        * ``o``: output device
        * ``base_image``: a `PIL.Image` to use as a base, if needed
        * ``name``: a name, for internal usage
        * ``interactive``: whether the canvas updates the display after each drawing
    """

    height = 0 #: height of canvas in pixels.
    width = 0 #: width of canvas in pixels.
    image = None #: ``PIL.Image`` object the ``Canvas`` is currently operating on.
    size = (0, 0) #: a tuple of (width, height).
    background_color = "black" #: default background color to use for drawing
    default_color = "white" #: default color to use for drawing
    default_font = None #: default font, referenced here to avoid loading it every time

    def __init__(self, o, base_image=None, name="", interactive=False):
        self.o = o
        if "b&w" not in o.type:
            raise ValueError("The output device supplied doesn't support pixel graphics!")
        if "color" in o.type:
            self.default_color = "lightseagreen"
        self.width = o.width
        self.height = o.height
        self.name = name
        self.size = (self.width, self.height)
        if base_image:
            assert(base_image.size == self.size)
            self.image = base_image.copy()
        else:
            self.image = Image.new(o.device_mode, self.size)
        self.draw = ImageDraw.Draw(self.image)
        self.fonts_dir = fonts_dir
        if not self.default_font:
            self.default_font = get_default_font()
        self.interactive = interactive

    def load_image(self, image):
        assert(image.size == self.size)
        self.image = image.copy()
        self.draw = ImageDraw.Draw(self.image)

    def load_font(self, path, size, alias=None, type="truetype"):
        """
        Loads a font by its path for the given size, then returns it.
        Also, stores the font in the ``canvas.py`` ``font_cache``
        dictionary, so that it doesn't have to be re-loaded later on.

        Supports both absolute paths, paths relative to root ZPUI
        directory and paths to fonts in the ZPUI font directory
        (``ui/fonts`` by default).
        """
        # For fonts in the font directory, can use the filename as a shorthand
        if path in os.listdir(self.fonts_dir):
            logger.debug("Loading font from the font storage directory")
            path = os.path.join(self.fonts_dir, path)
        # If an alias was not specified, using font filename as the alias (for caching)
        if alias is None:
            alias = os.path.basename(path)
        # Adding size to the alias and using it for caching
        font_name = "{}:{}".format(alias, size)
        logger.debug("Font alias: {}".format(font_name))
        # Font already loaded, returning the instance we have
        if font_name in font_cache:
            logger.debug("Font {} already loaded, returning".format(font_name))
            return font_cache[font_name]
        # We don't have it cached - let's see the type requested
        # We only support loading TrueType fonts, though
        elif type == "truetype":
            logger.debug("Loading a TT font from {}".format(font_name))
            font = ImageFont.truetype(path, size)
        else:
            raise ValueError("Font type not yet supported: {}".format(type))
        # We loaded a font, now let's cache it and return
        logger.debug("Caching and returning")
        font_cache[font_name] = font
        return font

    def decypher_font_reference(self, reference):
        """
        Is designed to detect the various ways that a ``font`` argument
        can be passed into a function, then return an ``ImageFont`` instance.
        """
        if reference is None:
            return self.default_font
        if reference in font_cache:
            # Got a font alias
            font = font_cache[reference]
        elif isinstance(reference, (tuple, list)):
            # Got a font path with the size parameter
            font = self.load_font(*reference)
        elif isinstance(reference, (ImageFont.ImageFont, ImageFont.FreeTypeFont)):
            font = reference
        else:
            return ValueError("Unknown font reference/object, type: {}".format(type(reference)))
        return font

    def point(self, coord_pairs, **kwargs):
        """
        Draw a point, or multiple points on the canvas. Coordinates are expected in
        ``((x1, y1), (x2, y2), ...)`` format, where ``x*`` & ``y*`` are coordinates
        of each point you want to draw.

        Keyword arguments:

          * ``fill``: point color (default: white, as default canvas color)
        """
        coord_pairs = self.check_coordinate_pairs(coord_pairs)
        fill = kwargs.pop("fill", self.default_color)
        self.draw.point(coord_pairs, fill=fill, **kwargs)
        self.display_if_interactive()

    def line(self, coords, **kwargs):
        """
        Draw a line on the canvas. Coordinates are expected in
        ``(x1, y1, x2, y2)`` format, where ``x1`` & ``y1`` are coordinates
        of the start, and ``x2`` & ``y2`` are coordinates of the end.

        Keyword arguments:

          * ``fill``: line color (default: white, as default canvas color)
          * ``width``: line width (default: 0, which results in a single-pixel-wide line)
        """
        fill = kwargs.pop("fill", self.default_color)
        coords = self.check_coordinates(coords, rearrange_coords=False)
        self.draw.line(coords, fill=fill, **kwargs)
        self.display_if_interactive()

    def text(self, text, coords, **kwargs):
        """
        Draw text on the canvas. Coordinates are expected in (x, y)
        format, where ``x`` & ``y`` are coordinates of the top left corner.

        You can pass a ``font`` keyword argument to it - it accepts either a
        ``PIL.ImageFont`` object or a tuple of ``(path, size)``, which are
        then supplied to ``Canvas.load_font()``.

        Do notice that order of first two arguments is reversed compared
        to the corresponding ``PIL.ImageDraw`` method.

        Keyword arguments:

          * ``fill``: text color (default: white, as default canvas color)
        """
        assert(isinstance(text, basestring))
        fill = kwargs.pop("fill", self.default_color)
        font = kwargs.pop("font", self.default_font)
        font = self.decypher_font_reference(font)
        coords = self.check_coordinates(coords)
        if text: # Errors out on empty text
            self.draw.text(coords, text, fill=fill, font=font, **kwargs)
            self.display_if_interactive()

    def vertical_text(self, text, coords, **kwargs):
        """
        Draw vertical text on the canvas. Coordinates are expected in (x, y)
        format, where ``x`` & ``y`` are coordinates of the top left corner.

        You can pass a ``font`` keyword argument to it - it accepts either a
        ``PIL.ImageFont`` object or a tuple of ``(path, size)``, which are
        then supplied to ``Canvas.load_font()``.

        Do notice that order of first two arguments is reversed compared
        to the corresponding ``PIL.ImageDraw`` method.

        Keyword arguments:

          * ``fill``: text color (default: white, as default canvas color)
        """
        assert(isinstance(text, basestring))
        fill = kwargs.pop("fill", self.default_color)
        font = kwargs.pop("font", self.default_font)
        charheight = kwargs.pop("charheight", None)
        font = self.decypher_font_reference(font)
        coords = self.check_coordinates(coords)
        char_coords = list(coords)
        if not charheight: # Auto-determining charheight if not available
            _, t, _, b = self.draw.textbbox((0, 0), "H", font=font)
            charheight = b-t
        for char in text:
            self.draw.text(char_coords, char, fill=fill, font=font, **kwargs)
            char_coords[1] += charheight
        self.display_if_interactive()

    def custom_shape_text(self, text, coords_cb, **kwargs):
        """
        Draw text on the canvas, getting the position for each character
        from a supplied function. Coordinates are expected in (x, y)
        format, where ``x`` & ``y`` are coordinates of the top left corner
        of the character.

        You can pass a ``font`` keyword argument to it - it accepts either a
        ``PIL.ImageFont`` object or a tuple of ``(path, size)``, which are
        then supplied to ``Canvas.load_font()``.

        Do notice that order of first two arguments is reversed compared
        to the corresponding ``PIL.ImageDraw`` method.

        Keyword arguments:

          * ``fill``: text color (default: white, as default canvas color)
        """
        assert(isinstance(text, basestring))
        fill = kwargs.pop("fill", self.default_color)
        font = kwargs.pop("font", self.default_font)
        charheight = kwargs.pop("charheight", None)
        font = self.decypher_font_reference(font)
        for i, char in enumerate(text):
            coords = coords_cb(i, char)
            coords = self.check_coordinates(coords)
            self.draw.text(coords, char, fill=fill, font=font, **kwargs)
        self.display_if_interactive()

    def rectangle(self, coords, **kwargs):
        """
        Draw a rectangle on the canvas. Coordinates are expected in
        ``(x1, y1, x2, y2)`` format, where ``x1`` & ``y1`` are coordinates
        of the top left corner, and ``x2`` & ``y2`` are coordinates
        of the bottom right corner.

        Keyword arguments:

          * ``outline``: outline color (default: white, as default canvas color)
          * ``fill``: fill color (default: None, as in, transparent)
        """
        coords = self.check_coordinates(coords)
        outline = kwargs.pop("outline", self.default_color)
        fill = kwargs.pop("fill", None)
        self.draw.rectangle(coords, outline=outline, fill=fill, **kwargs)
        self.display_if_interactive()

    def polygon(self, coord_pairs, **kwargs):
        """
        Draw a polygon on the canvas. Coordinates are expected in
        ``((x1, y1), (x2, y2), (x3, y3),  [...])`` format, where ``xX`` and ``yX``
        are points that construct a polygon.

        Keyword arguments:

          * ``outline``: outline color (default: white, as default canvas color)
          * ``fill``: fill color (default: None, as in, transparent)
        """
        coord_pairs = self.check_coordinate_pairs(coord_pairs)
        outline = kwargs.pop("outline", self.default_color)
        fill = kwargs.pop("fill", None)
        self.draw.polygon(coord_pairs, outline=outline, fill=fill, **kwargs)
        self.display_if_interactive()

    def circle(self, coords, **kwargs):
        """
        Draw a circle on the canvas. Coordinates are expected in
        ``(xc, yx, r)`` format, where ``xc`` & ``yc`` are coordinates
        of the circle center and ``r`` is the radius.

        Keyword arguments:

          * ``outline``: outline color (default: white, as default canvas color)
          * ``fill``: fill color (default: None, as in, transparent)
        """
        assert(len(coords) == 3), "Expects three arguments - x center, y center and radius!"
        radius = coords[2]
        coords = coords[:2]
        coords = self.check_coordinates(coords)
        outline = kwargs.pop("outline", self.default_color)
        fill = kwargs.pop("fill", None)
        ellipse_coords = (coords[0]-radius, coords[1]-radius, coords[0]+radius, coords[1]+radius)
        self.draw.ellipse(ellipse_coords, outline=outline, fill=fill, **kwargs)
        self.display_if_interactive()

    def ellipse(self, coords, **kwargs):
        """
        Draw a ellipse on the canvas. Coordinates are expected in
        ``(x1, y1, x2, y2)`` format, where ``x1`` & ``y1`` are coordinates
        of the top left corner, and ``x2`` & ``y2`` are coordinates
        of the bottom right corner.

        Keyword arguments:

          * ``outline``: outline color (default: white, as default canvas color)
          * ``fill``: fill color (default: None, as in, transparent)
        """
        coords = self.check_coordinates(coords)
        outline = kwargs.pop("outline", self.default_color)
        fill = kwargs.pop("fill", None)
        self.draw.ellipse(coords, outline=outline, fill=fill, **kwargs)
        self.display_if_interactive()

    def arc(self, coords, start, end, **kwargs):
        """
        Draw an arc on the canvas. Coordinates are expected in
        ``(x1, y1, x2, y2)`` format, where ``x1`` & ``y1`` are coordinates
        of the top left corner, and ``x2`` & ``y2`` are coordinates
        of the bottom right corner. ``start`` and ``end`` angles are
        measured in degrees (360 is a full circle), start at 0 (3 o'clock)
        and increase *clockwise*.

        .. code_block:: python
                270
              225  315
            180      0
              135  45
                 90

        Keyword arguments:

          * ``fill``: text color (default: white, as default canvas color)
        """
        coords = self.check_coordinates(coords, rearrange_coords=False)
        fill = kwargs.pop("fill", self.default_color)
        self.draw.arc(coords, start, end, fill=fill, **kwargs)
        self.display_if_interactive()

    def get_image(self):
        """
        Get the current ``PIL.Image`` object.
        """
        return self.image

    def get_center(self, x=None, y=None):
        """
        Get center coordinates. Will not represent the physical center -
        especially with those displays having even numbers as width and height
        in pixels (that is, the absolute majority of them).

        You can substitute width and height of your choice as ``x`` and ``y``,
        purely so you can quickly center things in arbitrary areas.
        """
        cx = self.width // 2 if x == None else x // 2
        cy = self.height // 2 if y == None else y // 2
        return cx, cy

    def invert(self):
        """
        Inverts the image that ``Canvas`` is currently operating on.
        """
        image = self.image
        # "1" won't invert, need "L"
        if image.mode == "1":
            image = image.convert("L")
        image = ImageOps.invert(image)
        # If was converted to "L", setting back to "1"
        if image.mode == "L" and self.o.device_mode == "1":
            image = image.convert("1")
        self.image = image
        self.display_if_interactive()

    def display(self):
        """
        Display the current image on the ``o`` object that was supplied to
        ``Canvas``.
        """
        self.o.display_image(self.image)

    def clear(self, coords=None, fill=None):
        # type: tuple -> None
        """
        Fill an area of the image with default background color. If coordinates are
        not supplied, fills the whole canvas, effectively clearing it. Uses the
        background color by default.
        """
        if coords is None:
            coords = (0, 0, self.width, self.height)
        if fill is None:
            fill = self.background_color
        coords = self.check_coordinates(coords)
        self.rectangle(coords, fill=fill, outline=fill)  # paint the background black first
        self.display_if_interactive()

    def check_coordinates(self, coords, check_count=True, rearrange_coords=True):
        # type: tuple -> tuple
        """
        A helper function to check and reformat coordinates supplied to
        functions. Currently, accepts integer coordinates, as well as strings
        - denoting offsets from opposite sides of the screen.
        """
        # Checking for string offset coordinates
        # First, we need to make coords into a mutable sequence - thus, a list
        coords = list(coords)
        for i, c in enumerate(coords):
            sign = "+"
            if isinstance(c, basestring):
                if c.startswith("-"):
                    sign = "-"
                    c = c[1:]
                assert c.isdigit(), "A numeric string expected, received: {}".format(coords[i])
                offset = int(c)
                dim = self.size[i % 2]
                if sign == "+":
                    coords[i] = dim + offset
                elif sign == "-":
                    coords[i] = dim - offset
            elif isinstance(c, float):
                logger.info("Received {} as a coordinate - pixel offsets can't be float, converting to int".format(c))
                coords[i] = int(c)
        # Restoring the status-quo
        coords = tuple(coords)
        # Now all the coordinates should be integers - if something slipped by the checks,
        # it's of type we don't process and we should raise an exception now
        for c in coords:
            assert isinstance(c, int), "{} not an integer or 'x' string!".format(c)
        if len(coords) == 2:
            return coords
        elif len(coords) == 4:
            # sanity checks for coordinates
            if rearrange_coords:
                x1, y1, x2, y2 = coords
                if (x1 >= x2):
                    x2, x1 = x1, x2
                    logger.info("x1 ({}) is smaller than x2 ({}), rearranging".format(x1, x2))
                if (y1 >= y2):
                    y2, y1 = y1, y2
                    logger.info("y1 ({}) is smaller than y2 ({}), rearranging".format(y1, y2))
                coords = x1, y1, x2, y2
            return coords
        else:
            if check_count:
                raise ValueError("Invalid number of coordinates!")
            else:
                return coords

    def check_coordinate_pairs(self, coord_pairs):
        # type: tuple -> tuple
        """
        A helper function to check and reformat coordinate pairs supplied to
        functions. Each pair is checked by ``check_coordinates``.
        """
        if not all([issequence(c) for c in coord_pairs]):
            # Didn't get pairs of coordinates - converting into pairs
            # But first, sanity checks
            assert (len(coord_pairs) % 2 == 0), "Odd number of coordinates supplied! ({})".format(coord_pairs)
            assert all([isinstance(i, (int, basestring)) for i in coord_pairs]), "Coordinates are non-uniform! ({})".format(coord_pairs)
            coord_pairs = convert_flat_list_into_pairs(coord_pairs)
        coord_pairs = list(coord_pairs)
        for i, coord_pair in enumerate(coord_pairs):
            coord_pairs[i] = self.check_coordinates(coord_pair)
        return tuple(coord_pairs)

    def centered_text(self, text, cw=None, ch=None, font=None):
        # type: str -> None
        """
        Draws centered text on the canvas. This is mostly a convenience function,
        used in some UI elements. You can also pass alternate
        screen center values so that text is centered related to those,
        as opposed to the real screen center.

        """
        font = self.decypher_font_reference(font)
        coords = self.get_centered_text_bounds(text, font=font, ch=ch, cw=cw)
        self.text(text, (coords.left, coords.top), font=font)
        self.display_if_interactive()

    def get_text_bounds(self, text, font=None):
        # type: str -> Rect
        """
        Returns the dimensions for a given text. If you use a
        non-default font, pass it as ``font``.
        """
        if text == "":
            return (0, 0)
        font = self.decypher_font_reference(font)
        l, t, r, b = self.draw.textbbox((0, 0), text, font=font)
        w, h = r-l, b-t
        return w, h

    def get_centered_text_bounds(self, text, cw=None, ch=None, x=None, y=None, font=None):
        # type: str -> Rect
        """
        Returns the coordinates for the text to be centered on the screen.
        The coordinates come wrapped in a ``Rect`` object. If you use a
        non-default font, pass it as ``font``. You can also pass alternate
        screen center values so that text is centered related to those,
        as opposed to the real screen center.
        """
        w, h = self.get_text_bounds(text, font=font)
        # Text center width and height
        tcw = w // 2
        tch = h // 2
        # Real center width and height
        rcw, rch = self.get_center(x=x, y=y)
        # If no values supplied as arguments (likely), using the real ones
        cw = cw if (cw is not None) else rcw
        ch = ch if (ch is not None) else rch
        return Rect(cw - tcw, ch - tch, cw + tcw, ch + tch)

    def invert_rect(self, coords):
        # type: tuple -> tuple
        """
        Inverts the image in the given rectangle region. Is useful for
        highlighting a part of the image, for example.
        """

        coords = self.check_coordinates(coords)
        image_subset = self.image.crop(coords)

        if image_subset.mode == "1":
            # PIL can't invert "1" mode - need to use "L"
            image_subset = image_subset.convert("L")
            image_subset = ImageOps.invert(image_subset)
            image_subset = image_subset.convert(self.o.device_mode)
        else: # Other mode - invert without workarounds
            image_subset = ImageOps.invert(image_subset)

        #self.clear(coords) # results in an unfun bug??
        self.image.paste(image_subset, (coords[0], coords[1]))

        self.display_if_interactive()

#    def rotate(self, degrees, expand=True):
#	"""
#	Rotates the image clockwise by the given amount of degrees. If
#	expand is set to False part of the original image may be cut
#	off.
#
#	TODO: define behaviour and goals of this function better.
#	For now, doesn't recalculate the canvas size, regenerate the
#	``ImageDraw`` object or impose any restrictions.
#	"""
#
#	self.image = self.image.rotate(degrees, expand=expand)

    def paste(self, image_or_path, coords=None, invert=False, mask="auto"):
        """
        Pastes the supplied image onto the canvas, with optional
        coordinates. Otherwise, you can supply a string path to an image
            that will be opened and pasted.

        If ``coords`` is not supplied, the image will be pasted in the top left
        corner. ``coords`` can be a 2-tuple giving the upper left
        corner or a 4-tuple defining the left, upper, right and lower
        pixel coordinate. If a 4-tuple is given, the size of the pasted
        image must match the size of the region.
        """

        if coords is not None:
            coords = self.check_coordinates(coords)
        if isinstance(image_or_path, basestring):
            image = Image.open(image_or_path)
        else:
            image = image_or_path
        # mask parameter for alpha channel cognizant pasting
        if mask == "auto":
            mask = image.mode == "RGBA"
        if mask == True:
            self.image.paste(image, box=coords, mask=image)
        else:
            self.image.paste(image, box=coords)
        # inverted only after drawing
        if invert:
            if not coords: coords = (0, 0)
            coords = coords+(coords[0]+image.width, coords[1]+image.height)
            self.invert_rect(coords)

    def display_if_interactive(self):
        if self.interactive:
            self.display()

    def __getattr__(self, name):
        if hasattr(self.draw, name):
            return getattr(self.draw, name)
        raise AttributeError


class MockOutput(object):
    """
    A mock output device that you can use to draw icons and other bitmaps using
    ``Canvas``.

    Keyword arguments:

      * ``width``
      * ``height``
      * ``type``: ZPUI output device type list (``["b&w"]`` by default)
      * ``device_mode``: PIL device.mode attribute (by default, ``'1'``)
    """
    default_width = 128
    default_height = 128
    default_type = ["b&w"]
    default_device_mode = '1'

    def __init__(self, width=None, height=None, type=None, device_mode=None, o=None):
        # now overriding parameters
        # first supplied arguments, then o. parameters, then defaults
        self.width = width if width else (o.width if o else self.default_width)
        self.height = height if height else (o.height if o else self.default_height)
        self.type = type if type else (o.type if o else self.default_type)
        self.device_mode = device_mode if device_mode else (o.device_mode if o else self.default_device_mode)

    def display_image(self, *args):
        return True


def expand_coords(coords, expand_by):
    """
    A simple method to expand 4 coordinates: x1, y1, x2, y2.
    If expand_by is an integer/float, will do x1-v, y1-v, x2+v, y2+v.
    If expand_by is a list of 4 values, will do x1-v1, y1-v1, x2+v2, y2+v2.
    """
    if len(coords) != 4:
        raise ValueError("expand_coords expects a tuple/list of 4 coordinates for 'coords', got {}".format(coords))
    if not isinstance(expand_by, (int, float, list, tuple)):
        raise ValueError("expand_coords expects an int/float/list/tuple as 'expand_by', got {} ({})".format(expand_by, type(expand_by)))
    if isinstance(expand_by, (list, tuple)) and len(expand_by) != 4:
        raise ValueError("expand_coords expects a 4-element list/tuple as 'expand_by', got {} ({} elements)".format(expand_by, len(expand_by)))
    a, b, c, d = coords
    e = expand_by
    if isinstance(expand_by, (int, float)):
        return (a-e, b-e, c+e, d+e)
    else:
        return (a-e[0], b-e[1], c+e[2], d+e[3])

def crop(image, min_width=None, min_height=None, align=None):
    bbox = image.getbbox()
    if bbox is None:
        return Image.new(image.mode, (0, 0))
    image = image.crop(bbox)
    border = [0, 0, 0, 0]
    if min_width and image.width<min_width:
        border[0 if align == "right" else 2]=min_width-image.width
    if min_height and image.height<min_height:
        border[1 if align == "bottom" else 3]=min_height-image.height
    if border != [0, 0, 0, 0]:
        image = ImageOps.expand(image, border=tuple(border), fill=Canvas.background_color)
    return image

def convert_flat_list_into_pairs(l):
    pl = []
    for i in range(len(l)//2):
        pl.append((l[i*2], l[i*2+1]))
    return pl

def replace_color(icon, fromc, toc):
    icon = icon.convert("RGBA")
    # from https://stackoverflow.com/questions/3752476/python-pil-replace-a-single-rgba-color
    if isinstance(fromc, str):
        fromc = ImageColor.getrgb(fromc)
    data = np.array(icon)
    r, g, b, a = data.T
    areas = (r == fromc[0]) & (g == fromc[1]) & (b == fromc[2])
    if isinstance(toc, str):
        toc = ImageColor.getrgb(toc)
    data[..., :-1][areas.T] = toc
    return Image.fromarray(data)

def swap_colors(icon, fromc1, toc1, fromc2, toc2):
    icon = icon.convert("RGBA")
    # from https://stackoverflow.com/questions/3752476/python-pil-replace-a-single-rgba-color
    if isinstance(fromc1, str):
        fromc1 = ImageColor.getrgb(fromc1)
    if isinstance(fromc2, str):
        fromc2 = ImageColor.getrgb(fromc2)
    data = np.array(icon)
    r, g, b, a = data.T
    areas1 = (r == fromc1[0]) & (g == fromc1[1]) & (b == fromc1[2])
    areas2 = (r == fromc2[0]) & (g == fromc2[2]) & (b == fromc2[2])
    if isinstance(toc1, str):
        toc1 = ImageColor.getrgb(toc1)
    if isinstance(toc2, str):
        toc2 = ImageColor.getrgb(toc2)
    data[..., :-1][areas1.T] = toc1
    data[..., :-1][areas2.T] = toc2
    return Image.fromarray(data)
