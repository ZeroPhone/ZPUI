"""test for PathPicker"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import PathPicker, MenuExitException
except ImportError:
    print("Absolute imports failed, trying relative imports")
    from zpui_lib.hacks import basestring_hack; basestring_hack()
    os.sys.path.append(os.path.dirname(os.path.abspath('.')))
    fonts_dir = "fonts"
    # Store original __import__
    orig_import = __import__

    def import_mock(name, *args):
        if name in ['helpers']:
            return Mock()
        elif name == 'ui.utils':
            import utils
            return utils
        elif name == 'ui.entry':
            import entry
            return entry
        elif name == 'ui.base_list_ui':
            import base_list_ui
            return base_list_ui
        elif name == 'ui.base_ui':
            import base_ui
            return base_ui
        elif name == 'ui.menu':
            import menu
            return menu
        elif name == 'ui.printer':
            import printer
            return printer
        elif name == 'ui.refresher':
            import refresher
            return refresher
        elif name == 'ui.number_input':
            import number_input
            return number_input
        elif name == 'ui.loading_indicators':
            import loading_indicators
            return loading_indicators
        elif name == 'ui.canvas':
            import canvas
            canvas.fonts_dir = "../fonts/"
            return canvas
        elif name == 'ui.funcs':
            import funcs
            return funcs
        return orig_import(name, *args)

    try:
        import __builtin__
    except ImportError:
        import builtins
        with patch('builtins.__import__', side_effect=import_mock):
            import canvas
            canvas.fonts_dir = "../fonts/"
            Canvas = canvas.Canvas
            expand_coords = canvas.expand_coords
            from path_picker import PathPicker, MenuExitException
    else:
        with patch('__builtin__.__import__', side_effect=import_mock):
            import canvas
            canvas.fonts_dir = "../fonts/"
            Canvas = canvas.Canvas
            expand_coords = canvas.expand_coords
            from path_picker import PathPicker, MenuExitException

def get_mock_input():
    return Mock()

def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m


pp_name = "Test PathPicker"


class TestPathPicker(unittest.TestCase):
    """tests dialog box class"""

    def test_constructor(self):
        """tests constructor"""
        pp = PathPicker("/tmp", get_mock_input(), get_mock_output(), name=pp_name, config={})
        self.assertIsNotNone(pp)

    def test_keymap(self):
        """tests keymap"""
        pp = PathPicker("/tmp", get_mock_input(), get_mock_output(), name=pp_name, config={})
        self.assertIsNotNone(pp.keymap)
        for key_name, callback in pp.keymap.items():
            self.assertIsNotNone(callback)

    def test_left_key_returns_none(self):
        pp = PathPicker('/tmp', get_mock_input(), get_mock_output(), name=pp_name, config={})
        pp.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            pp.deactivate()  # KEY_LEFT
            assert not pp.in_foreground

        with patch.object(pp, 'idle_loop', side_effect=scenario) as p:
            return_value = pp.activate()
        assert return_value is None

        # Checking after going a couple of elements down
        def scenario():
            for i in range(3):
                pp.move_down()  # KEY_DOWN x3
            pp.deactivate()  # KEY_LEFT
            assert not pp.in_foreground

        with patch.object(pp, 'idle_loop', side_effect=scenario) as p:
            return_value = pp.activate()
        assert return_value is None

    def test_left_key_returns_none_onlydirs(self):
        pp = PathPicker('/tmp', get_mock_input(), get_mock_output(), dirs_only=True, name=pp_name, config={})
        pp.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            pp.deactivate()  # KEY_LEFT
            assert not pp.in_foreground

        with patch.object(pp, 'idle_loop', side_effect=scenario) as p:
            return_value = pp.activate()
        assert return_value is None

    def test_enter_returns_something(self):
        dir_name = "zpui_pp_test_dir"
        dir2_name = "zpui_pp_test_dir2"
        os.mkdir(dir_name)
        os.mkdir(os.path.join(dir_name, dir2_name))
        pp = PathPicker(dir_name, get_mock_input(), get_mock_output(), name=pp_name, config={})
        pp.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            pp.move_down()  # KEY_DOWN; avoid the '..' entry
            try:
                pp.option_select(pp.path) # KEY_ENTER
            except MenuExitException:
                pass
            assert not pp.in_foreground

        with patch.object(pp, 'idle_loop', side_effect=scenario) as p:
            return_value = pp.activate()
        os.rmdir(os.path.join(dir_name, dir2_name))
        os.rmdir(dir_name)
        assert return_value is not None


if __name__ == '__main__':
    unittest.main()
