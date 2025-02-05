"""test for IntegerAdjustInput"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import IntegerAdjustInput
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
        from number_input import IntegerAdjustInput

def get_mock_input():
    return Mock()


def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m

shorthands = {
    "u":"KEY_UP",
    "d":"KEY_DOWN",
    "p":"KEY_F3",
    "q":"KEY_F4",
    "l":"KEY_LEFT",
    "r":"KEY_RIGHT",
    "e":"KEY_ENTER"}

def execute_shorthand(ii, shorthand):
    # A helper function for us to easier test behaviour of IntegerAdjustInput
    shorthand_key = shorthands[shorthand]
    ii.keymap[shorthand_key]()

ii_name = "Test IntegerAdjustInput"


class TestIntegerAdjustInput(unittest.TestCase):
    """test IntegerAdjustInput class"""

    def test_constructor(self):
        """tests constructor"""
        ii = IntegerAdjustInput(1, get_mock_input(), get_mock_output(), name=ii_name)
        self.assertIsNotNone(ii)

    def test_left_returns_none(self):
        ii = IntegerAdjustInput(1, get_mock_input(), get_mock_output(), name=ii_name)
        ii.refresh = lambda *args, **kwargs: None #not needed

        # Checking without changing value
        def scenario():
            ii.keymap["KEY_LEFT"]()
            assert not ii.in_foreground

        with patch.object(ii, 'idle_loop', side_effect=scenario) as p:
            return_value = ii.activate()
        assert return_value is None

        # Checking after entering some keys
        test_keys = "u"*5
        def scenario():
            for key in test_keys:
                execute_shorthand(ii, key)
            execute_shorthand(ii, 'l')
            assert not ii.in_foreground

        with patch.object(ii, 'idle_loop', side_effect=scenario) as p:
            return_value = ii.activate()
        assert return_value is None

    def test_entering_value(self):
        ii = IntegerAdjustInput(1, get_mock_input(), get_mock_output(), name=ii_name)
        ii.refresh = lambda *args, **kwargs: None

        plus = 5
        minus = 4
        expected = 2

        def scenario():
            for i in range(plus):
                execute_shorthand(ii, "u")
            for i in range(minus):
                execute_shorthand(ii, "d")
            execute_shorthand(ii, 'e')
            assert not ii.is_active

        with patch.object(ii, 'idle_loop', side_effect=scenario) as p:
            return_value = ii.activate()
        assert return_value == expected

    def test_pageup_pagedown(self):
        ii = IntegerAdjustInput(0, get_mock_input(), get_mock_output(), name=ii_name)
        ii.refresh = lambda *args, **kwargs: None

        plus = 5
        minus = 4
        expected = 10

        def scenario():
            for i in range(plus):
                execute_shorthand(ii, "p")
            for i in range(minus):
                execute_shorthand(ii, "q")
            execute_shorthand(ii, 'e')
            assert not ii.is_active

        with patch.object(ii, 'idle_loop', side_effect=scenario) as p:
            return_value = ii.activate()
        assert return_value == expected

    def test_shows_data_on_screen(self):
        """Tests whether the IntegerAdjustInput outputs data on screen when it's ran"""
        i = get_mock_input()
        o = get_mock_output()
        ii = IntegerAdjustInput(1, i, o, message="Test:", name=ii_name)

        def scenario():
            assert o.display_data.called
            assert o.display_data.call_args[0][0].strip() == 'Test:'
            assert o.display_data.call_args[0][1].strip() == str(1)
            for i in range(5):
                execute_shorthand(ii, "u")
                assert o.display_data.call_args[0][1].strip() == str(i+2)
            execute_shorthand(ii, "e")
            assert not ii.in_foreground  # Should exit on last "e"

        with patch.object(ii, 'idle_loop', side_effect=scenario) as p:
            ii.activate()
            #The scenario should only be called once
            assert ii.idle_loop.called
            assert ii.idle_loop.call_count == 1

        assert o.display_data.call_count == 6

if __name__ == '__main__':
    unittest.main()
