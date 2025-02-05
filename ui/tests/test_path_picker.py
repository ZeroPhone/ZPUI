"""test for PathPicker"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import PathPicker
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
        from path_picker import PathPicker

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


if __name__ == '__main__':
    unittest.main()
