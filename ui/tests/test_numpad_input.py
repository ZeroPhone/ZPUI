"""test for NumpadCharInput"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import NumpadCharInput, NumpadPasswordInput
except ImportError:
    print("Absolute imports failed, trying relative imports")
    os.sys.path.append(os.path.dirname(os.path.abspath('.')))
    # Store original __import__
    orig_import = __import__

    def import_mock(name, *args):
        if name in ['helpers']:
            m = Mock()
            m.configure_mock(cb_needs_key_state=lambda x:x, KEY_PRESSED=1, KEY_RELEASED=0, KEY_HELD=2)
            return m
        elif name == 'ui.utils':
            import utils
            return utils
        return orig_import(name, *args)

    with patch('__builtin__.__import__', side_effect=import_mock):
        from numpad_input import NumpadCharInput, NumpadPasswordInput

def get_mock_input():
    return Mock(maskable_keymap=["KEY_LEFT"])


def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m

def execute_key_sequence(ni, key_sequence):
    for key in key_sequence:
        key = "KEY_{}".format(key)
        if key in ni.action_keys:
            ni.keymap[key]()
        else:
            ni.process_streaming_keycode(key)


ni_name = "Test NumpadCharInput"


class TestNumpadCharInput(unittest.TestCase):
    """test NumpadCharInput class"""

    cls = NumpadCharInput

    def test_constructor(self):
        """tests constructor"""
        ni = self.cls(get_mock_input(), get_mock_output(), name=ni_name)
        self.assertIsNotNone(ni)

    def test_action_keys_leakage(self):
        """tests whether the action key settings of one NumpadCharInput leaks into another"""
        i = get_mock_input()
        o = get_mock_output()
        i1 = self.cls(i, o, name=ni_name + "1")
        i1.action_keys["F1"] = "accept_value"
        i2 = self.cls(i, o, name=ni_name + "2")
        i1.action_keys["F1"] = "accept_value"
        i2.action_keys["ENTER"] = "deactivate"
        i3 = self.cls(i, o, name=ni_name + "3")
        assert (i1.action_keys != i2.action_keys)
        assert (i2.action_keys != i3.action_keys)
        assert (i1.action_keys != i3.action_keys)

    def test_f1_left_returns_none(self):
        ni = self.cls(get_mock_input(), get_mock_output(), name=ni_name)
        ni.refresh = lambda *args, **kwargs: None #not needed

        # Checking at the start of the list
        def scenario():
            ni.keymap["KEY_LEFT"]()
            assert not ni.in_foreground

        with patch.object(ni, 'idle_loop', side_effect=scenario) as p:
            return_value = ni.activate()
        assert return_value is None

        # Checking at the end of the list
        def scenario():
            for i in range(3):
                ni.process_streaming_keycode("KEY_1")
            ni.keymap["KEY_F1"]()
            assert not ni.in_foreground

        with patch.object(ni, 'idle_loop', side_effect=scenario) as p:
            return_value = ni.activate()
        assert return_value is None

    def test_entering_value(self):
        ni = self.cls(get_mock_input(), get_mock_output(), name=ni_name)
        ni.refresh = lambda *args, **kwargs: None

        #Defining a key sequence to be tested
        key_sequence = [4, 4, 3, 3, 5, 5, 5, "RIGHT", 5, 5, 5, 6, 6, 6, "ENTER"]
        expected_output = "hello"

        def scenario():
            execute_key_sequence(ni, key_sequence)
            assert not ni.in_foreground  # Should not be active

        with patch.object(ni, 'idle_loop', side_effect=scenario) as p:
            return_value = ni.activate()
        assert return_value == expected_output

    def test_entering_value_with_backspaces(self):
        ni = self.cls(get_mock_input(), get_mock_output(), name=ni_name)
        ni.refresh = lambda *args, **kwargs: None

        # Pressing backspace a couple of times
        key_sequence = [4, 4, 1, "F2", 3, 3, "F2", 3, 3, 5, 5, 5, "RIGHT", 1, "F2", 5, 5, 5, 6, 6, 6, 1, 1, "ENTER"]
        expected_output = "hello!"
        def scenario():
            execute_key_sequence(ni, key_sequence)
            assert not ni.in_foreground  # Should not be active

        with patch.object(ni, 'idle_loop', side_effect=scenario) as p:
            return_value = ni.activate()
        assert return_value == expected_output

    def test_shows_data_on_screen(self):
        """Tests whether the NumpadCharInput outputs data on screen when it's ran"""
        i = get_mock_input()
        o = get_mock_output()
        ni = self.cls(i, o, message="Test:", name=ni_name)

        def scenario():
            ni.deactivate()

        with patch.object(ni, 'idle_loop', side_effect=scenario) as p:
            ni.activate()
            #The scenario should only be called once
            assert ni.idle_loop.called
            assert ni.idle_loop.call_count == 1

        assert o.display_data.called
        assert o.display_data.call_count == 1 #One in to_foreground
        assert o.display_data.call_args[0] == ('Test:', '', '', '', '', '', '', ' Cancel   OK   Erase ')


class TestNumpadPasswordInput(TestNumpadCharInput):
    """test NumpadPasswordInput class"""
    cls = NumpadPasswordInput


if __name__ == '__main__':
    unittest.main()
