import os

from PIL import Image, ImageDraw, ImageOps, ImageFont

from ui.utils import Rect

from coords import check_coordinates, check_coordinate_pairs, convert_flat_list_into_pairs

fonts_dir = "ui/fonts/"
font_cache = {}

default_font = None
def get_default_font():
    global default_font
    if not default_font:
        default_font = ImageFont.load_default()
    return default_font

from helpers import setup_logger
logger = setup_logger(__name__, "warning")

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
    fonts_dir = fonts_dir

    def __init__(self, o, base_image=None, name="", interactive=False):
        self.o = o
        if "b&w-pixel" not in o.type:
            raise ValueError("The output device supplied doesn't support pixel graphics!")
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
        coord_pairs = check_coordinate_pairs(self, coord_pairs)
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
        coords = check_coordinates(self, coords)
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
        coords = check_coordinates(self, coords)
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
        coords = check_coordinates(self, coords)
        char_coords = list(coords)
        if not charheight: # Auto-determining charheight if not available
            _, charheight = self.draw.textsize("H", font=font)
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
            coords = check_coordinates(self, coords)
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
        coords = check_coordinates(self, coords)
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
        coord_pairs = check_coordinate_pairs(self, coord_pairs)
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
        coords = check_coordinates(self, coords)
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
        coords = check_coordinates(self, coords)
        outline = kwargs.pop("outline", self.default_color)
        fill = kwargs.pop("fill", None)
        self.draw.ellipse(coords, outline=outline, fill=fill, **kwargs)
        self.display_if_interactive()

    def get_image(self):
        """
        Get the current ``PIL.Image`` object.
        """
        return self.image

    def get_center(self):
        """
        Get center coordinates. Will not represent the physical center -
        especially with those displays having even numbers as width and height
        in pixels (that is, the absolute majority of them).
        """
        return self.width / 2, self.height / 2

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
        coords = check_coordinates(self, coords)
        self.rectangle(coords, fill=fill, outline=fill)  # paint the background black first
        self.display_if_interactive()

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
        # type: str -> tuple
        """
        Returns the dimensions for a given text. If you use a
        non-default font, pass it as ``font``.
        """
        if text == "":
            return (0, 0)
        font = self.decypher_font_reference(font)
        w, h = self.draw.textsize(text, font=font)
        return w, h

    def get_centered_text_bounds(self, text, cw=None, ch=None, font=None):
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
        tcw = w / 2
        tch = h / 2
        # Real center width and height
        rcw, rch = self.get_center()
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

        coords = check_coordinates(self, coords)
        image_subset = self.image.crop(coords)

        if image_subset.mode == "1":
            # PIL can't invert "1" mode - need to use "L"
            image_subset = image_subset.convert("L")
            image_subset = ImageOps.invert(image_subset)
            image_subset = image_subset.convert(self.o.device_mode)
        else: # Other mode - invert without workarounds
            image_subset = ImageOps.invert(image_subset)

        self.clear(coords)
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

    def paste(self, image_or_path, coords=None):
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
            image_or_path = Image.open(image_or_path)
	self.image.paste(image_or_path, box=coords)

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
      * ``type``: ZPUI output device type list (``["b&w-pixel"]`` by default)
      * ``device_mode``: PIL device.mode attribute (by default, ``'1'``)
    """

    def __init__(self, width=128, height=64, type=None, device_mode='1'):
        self.width = width
        self.height = height
        self.type = type if type else ["b&w-pixel"]
        self.device_mode = device_mode

    def display_image(self, *args):
        return True
