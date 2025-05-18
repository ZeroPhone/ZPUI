"""test for TextReader functions"""
import os
import unittest
from PIL import Image

from mock import patch, Mock

try:
    from ui import TextReader
except ImportError:
    print("Absolute imports failed, trying relative imports")
    from zpui_lib.hacks import basestring_hack; basestring_hack()
    os.sys.path.append(os.path.dirname(os.path.abspath('.')))
    # Store original __import__
    orig_import = __import__

    def import_mock(name, *args, **kwargs):
        if name in ['helpers']:
            return Mock()
        elif name == 'ui.utils':
            import utils
            return utils
        elif name == 'ui.canvas':
            import canvas
            canvas.fonts_dir = "../fonts/"
            return canvas
        elif name == 'ui.funcs':
            import funcs
            return funcs
        return orig_import(name, *args, **kwargs)

    try:
        import __builtin__
    except ImportError:
        import builtins
        with patch('builtins.__import__', side_effect=import_mock):
            from scrollable_element import TextReader
    else:
        with patch('__builtin__.__import__', side_effect=import_mock):
            from scrollable_element import TextReader

def get_mock_input():
    return Mock()

def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m

def get_mock_graphical_output(width, height, mode="1", cw=6, ch=8):
    m = get_mock_output(rows=width//cw, cols=height//ch)
    m.configure_mock(width=width, height=height, device_mode=mode, char_height=ch, char_width=cw, type=["b&w"])
    return m

class TestTextReader(unittest.TestCase):
    """tests TextReader functions"""

    def test_shows_data_on_screen_def_res(self):
        """Tests whether the TextReader outputs data on screen when it's ran, with a 128x64 resolution screen"""
        i = get_mock_input()
        o = get_mock_graphical_output(128, 64)

        tr = TextReader("test", i, o, 0, autohide_scrollbars=False)
        def scenario():
            """
            assert tr.contents[0][0] == "False"
            tr.select_entry()
            assert tr.contents[0][0] == "True"
            tr.select_entry()
            assert tr.contents[0][0] == "False"
            """
            tr.deactivate()
            assert not tr.in_foreground

        with patch.object(tr, 'idle_loop', side_effect=scenario) as p:
            tr.activate()

        assert o.display_image.called
        assert o.display_image.call_count == 1

    def test_shows_data_on_screen_beepy_res(self):
        """Tests whether the TextReader outputs data on screen when it's ran, with a 400x240 resolution screen"""
        i = get_mock_input()
        o = get_mock_graphical_output(400, 240)

        tr = TextReader("test", i, o, 0, autohide_scrollbars=False)
        def scenario():
            """
            assert tr.contents[0][0] == "False"
            tr.select_entry()
            assert tr.contents[0][0] == "True"
            tr.select_entry()
            assert tr.contents[0][0] == "False"
            """
            tr.deactivate()
            assert not tr.in_foreground

        with patch.object(tr, 'idle_loop', side_effect=scenario) as p:
            tr.activate()

        assert o.display_image.called
        assert o.display_image.call_count == 1

    def test_scrollbars_get_hidden(self):
        """Tests whether the TextReader's hideable scrollbars get hidden"""
        i = get_mock_input()
        o = get_mock_graphical_output(400, 240)

        tr = TextReader("test", i, o, 0, autohide_scrollbars=True, fade_time=0)
        cnt = 0
        def scenario():
            nonlocal cnt
            """
            assert tr.contents[0][0] == "False"
            tr.select_entry()
            assert tr.contents[0][0] == "True"
            tr.select_entry()
            assert tr.contents[0][0] == "False"
            """
            cnt += 1
            #tr.refresh()
            if cnt == 2: # might need one more loop iteration for scrollbars to get hidden
                tr.deactivate()
                assert not tr.in_foreground

        with patch.object(tr, 'idle_loop', side_effect=scenario) as p:
            tr.activate()

        assert o.display_image.called
        assert o.display_image.call_count == 2

    def test_works_with_empty_string(self):
        """Tests whether the TextReader doesn't crash and outputs data on screen when it's ran with empty string supplied as `text`"""
        i = get_mock_input()
        o = get_mock_graphical_output(128, 64)

        tr = TextReader("", i, o, 0, autohide_scrollbars=False)
        def scenario():
            """
            assert tr.contents[0][0] == "False"
            tr.select_entry()
            assert tr.contents[0][0] == "True"
            tr.select_entry()
            assert tr.contents[0][0] == "False"
            """
            tr.deactivate()
            assert not tr.in_foreground

        with patch.object(tr, 'idle_loop', side_effect=scenario) as p:
            tr.activate()

        assert o.display_image.called
        assert o.display_image.call_count == 1


if __name__ == '__main__':
    unittest.main()
