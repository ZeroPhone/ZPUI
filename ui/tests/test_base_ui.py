"""test for BaseListUIElement"""
import os
import unittest

from mock import patch, Mock

try:
    from ui.base_ui import BaseUIElement
except ImportError as e:
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
        from base_ui import BaseUIElement

def get_mock_input():
    return Mock()

def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m

def get_mock_graphical_output(width=128, height=64, mode="1", cw=6, ch=8):
    m = get_mock_output(rows=width//cw, cols=height//ch)
    m.configure_mock(width=width, height=height, device_mode=mode, char_height=ch, char_width=cw, type=["b&w"])
    return m

el_name = "Test BaseUIElement"


class UIElementTest(BaseUIElement):
    def generate_keymap(self):
        return {}

class TestBaseUIElement(unittest.TestCase):
    """tests base ui element class"""

    @unittest.skip("test takes too long by default because of how it interacts with the unittest library. run manually if needed")
    def test_constructor_generates_name_if_not_supplied(self):
        """tests constructor"""
        element = UIElementTest(get_mock_input(), get_mock_output(), name=None)
        self.assertIsNotNone(element.name)


if __name__ == '__main__':
    unittest.main()
