"""test for Printer functions"""
import os
import unittest
from PIL import Image

from mock import patch, Mock

try:
    from ui import Canvas, Printer, GraphicsPrinter
except ImportError:
    print("Absolute imports failed, trying relative imports")
    os.sys.path.append(os.path.dirname(os.path.abspath('.')))
    # Store original __import__
    orig_import = __import__

    def import_mock(name, *args, **kwargs):
        if name in ['helpers']:
            return Mock()
        elif name == 'ui.utils':
            import utils
            return utils
        return orig_import(name, *args, **kwargs)

    with patch('__builtin__.__import__', side_effect=import_mock):
        from printer import Printer, GraphicsPrinter
    from canvas import Canvas

def get_mock_input():
    return Mock()

def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m

def get_mock_graphical_output(width, height, mode="1", cw=6, ch=8):
    m = get_mock_output(rows=width/cw, cols=height/ch)
    m.configure_mock(width=width, height=height, device_mode=mode, char_height=ch, char_width=cw, type=["b&w"])
    return m

def easy_graphics_test(image, width, height):
    o = get_mock_graphical_output(width, height)
    GraphicsPrinter(image, None, o, 0)
    assert o.display_image.called
    resized_image = o.display_image.call_args[0][0]
    print(resized_image.size)
    assert resized_image.size == (width, height)

class TestPrinter(unittest.TestCase):
    """tests Printer functions"""
    def test_runs_with_none_i(self):
        """tests constructor"""
        assert Printer("test", None, get_mock_output(), 0) == None

    def test_graphical_printer(self):
        image = Canvas(get_mock_graphical_output(128,64)).get_image()
        easy_graphics_test(image,128,64)
        easy_graphics_test(image,128,121)
        easy_graphics_test(image,128,37)
        easy_graphics_test(image,143,64)
        easy_graphics_test(image,31,64)
        easy_graphics_test(image,56,75)
        easy_graphics_test(image,139,37)
        easy_graphics_test(image,53,42)
        easy_graphics_test(image,167,153)

    def test_shows_data_on_screen(self):
        """Tests whether the Printer outputs data on screen when it's ran"""
        i = get_mock_input()
        o = get_mock_output()

        Printer("test", i, o, 0)

        assert o.display_data.called
        assert o.display_data.call_count == 1
        assert o.display_data.call_args[0] == ('test',)

if __name__ == '__main__':
    unittest.main()
