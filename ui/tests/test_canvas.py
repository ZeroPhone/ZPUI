"""tests for Canvas"""
import os
import unittest

from mock import patch, Mock
from PIL import Image, ImageFont, ImageChops

try:
    from ui import Canvas
except ImportError:
    print("Absolute imports failed, trying relative imports")
    os.sys.path.append(os.path.dirname(os.path.abspath('.')))
    # Store original __import__
    orig_import = __import__

    def import_mock(name, *args):
        if name in ['helpers']:
            return Mock()
        elif name == 'ui.utils':
            import utils
            return utils
        return orig_import(name, *args)

    with patch('__builtin__.__import__', side_effect=import_mock):
        from canvas import Canvas


def get_mock_output(width=128, height=64, mode="1"):
    m = Mock()
    m.configure_mock(width=width, height=height, device_mode=mode, type=["b&w-pixel"])
    return m


c_name = "Test Canvas"


class TestCanvas(unittest.TestCase):
    """Tests the Canvas class"""

    def test_constructor(self):
        """Tests constructor"""
        c = Canvas(get_mock_output(), name=c_name)
        self.assertIsNotNone(c)

    def test_base_image(self):
        """Tests whether the base_image kwarg works"""
        w = 128
        h = 64
        i = Image.new("1", (w, h) )
        c = Canvas(get_mock_output(), base_image=i, name=c_name)
        assert(c.image == i)
        assert(c.size == (w, h))

    def test_howto_example_drawing_basics(self):
        """tests the first canvas example from howto"""
        test_image = get_image("canvas_1.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        c.point((1, 2))
        c.point( ( (2, 1), (2, 3), (3, 4) ) )
        c.display() # Shouldn't throw an exception
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_howto_example_drawing_text(self):
        """tests the first canvas example from howto"""
        test_image = get_image("canvas_2.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        c.text("Hello world", (0, 0))
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_howto_example_drawing_text(self):
        """tests the second text canvas example from howto"""
        test_image = get_image("canvas_7.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        c.centered_text("Hello world")
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_howto_example_drawing_centered_text(self):
        """tests the third text canvas example from howto"""
        test_image = get_image("canvas_8.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        ctc = c.get_centered_text_bounds("a")
        c.text("a", (ctc.left, 0))
        c.text("b", (str(ctc.left-ctc.right), ctc.top))
        c.text("c", (ctc.left, str(ctc.top-ctc.bottom)))
        c.text("d", (0, ctc.top))
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_custom_center_centered_text_coords(self):
        """tests the third text canvas example from howto"""
        test_image = get_image("canvas_11.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        ctc = c.get_centered_text_bounds("", ch=16, cw=32)
        c.text("a", (ctc.left, 0))
        c.text("b", (str(ctc.left-ctc.right), ctc.top))
        c.text("c", (ctc.left, str(ctc.top-ctc.bottom)))
        c.text("d", (0, ctc.top))
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_drawing_custom_shape_text(self):
        """tests the custom shape text drawing"""
        test_image = get_image("canvas_8.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        ctc = c.get_centered_text_bounds("a")
        def coords_cb(i, ch):
            return [(ctc.left, 0), (str(ctc.left-ctc.right), ctc.top),
                    (ctc.left, str(ctc.top-ctc.bottom)), (0, ctc.top)][i]
        c.custom_shape_text("abcd", coords_cb)
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_drawing_vertical_text(self):
        """tests the vertical text drawing"""
        test_image = get_image("canvas_9.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        c.vertical_text("Personal", (0, 0))
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_howto_example_drawing_line(self):
        """tests the third canvas example from howto"""
        test_image = get_image("canvas_3.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        c.line((10, 4, "-8", "-4"))
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_howto_example_drawing_rectangle(self):
        """tests the fourth canvas example from howto"""
        test_image = get_image("canvas_4.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        c.rectangle((10, 4, 20, "-10"))
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_howto_example_drawing_line(self):
        """tests the fifth canvas example from howto"""
        test_image = get_image("canvas_5.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        c.circle(("-8", 8, 4))
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_howto_example_invert_region(self):
        """tests the sixth canvas example from howto"""
        test_image = get_image("canvas_6.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        c.text("Hello world", (5, 5))
        c.invert_rect((35, 5, 80, 17))
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_invert(self):
        """tests that inversion works with default display"""
        test_image = get_image("canvas_10.png")
        o = get_mock_output()
        c = Canvas(o, name=c_name)
        c.text("Hello world", (5, 5))
        c.invert()
        assert(c.get_image().mode == o.device_mode)
        assert(imgs_are_equal(c.get_image(), test_image))

    def test_invert_region_rgb(self):
        """tests that rgb canvas inversion doesn't fail with RGB displays and returns a valid RGB image"""
        test_image = get_image("canvas_6.png")
        o = get_mock_output(mode="RGB")
        c = Canvas(o, name=c_name)
        c.text("Hello world", (5, 5))
        c.invert_rect((35, 5, 80, 17))
        assert(c.get_image().mode == o.device_mode)
        assert(imgs_are_equal(c.get_image(), test_image.convert("RGB")))

    def test_invert_rgb(self):
        """tests that rgb canvas inversion doesn't fail with RGB displays and returns a valid RGB image"""
        test_image = get_image("canvas_10.png")
        o = get_mock_output(mode="RGB")
        c = Canvas(o, name=c_name)
        c.text("Hello world", (5, 5))
        c.invert()
        assert(c.get_image().mode == o.device_mode)
        assert(imgs_are_equal(c.get_image(), test_image.convert("RGB")))

#    def test_rotate(self):
#	test_image = get_image("canvas_12.png")
#	o = get_mock_output(mode="RGB")
#	c = Canvas(o, name=c_name)
#	c.text("Hello world", (5, 5))
#	c.rotate(90)
#	assert(c.get_image().mode == o.device_mode)
#	assert(imgs_are_equal(c.get_image(), test_image.convert("RGB")))

    def test_paste(self):
	test_image = get_image("canvas_13.png")
	image_to_paste = get_image("canvas_14.png")
	o = get_mock_output(mode="RGB")
	c = Canvas(o, name=c_name)
	c.text("Hello world", (16, 16))
	c.paste(image_to_paste)
	assert(c.get_image().mode == o.device_mode)
	assert(imgs_are_equal(c.get_image(), test_image.convert("RGB")))

def imgs_are_equal(i1, i2):
    return ImageChops.difference(i1, i2).getbbox() is None

def get_image(path):
    if path not in os.listdir('.'):
        path = os.path.join('ui/tests/', path)
    return Image.open(path)

if __name__ == '__main__':
    unittest.main()
