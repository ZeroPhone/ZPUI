"""test for Checkbox"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import Checkbox, Entry
    from ui.base_list_ui import Canvas
    fonts_dir = "ui/fonts"
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
        from checkbox import Checkbox
        from base_list_ui import Canvas
        from entry import Entry
        fonts_dir = "../fonts"

def get_mock_input():
    return Mock()

def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m

def get_mock_graphical_output(width=128, height=64, mode="1", cw=6, ch=8):
    m = get_mock_output(rows=width/cw, cols=height/ch)
    m.configure_mock(width=width, height=height, device_mode=mode, char_height=ch, char_width=cw, type=["b&w"])
    return m

cb_name = "Test checkbox"


class TestCheckbox(unittest.TestCase):
    """tests dialog box class"""

    def test_constructor(self):
        """tests constructor"""
        checkbox = Checkbox([["Option", "option"]], get_mock_input(), get_mock_output(), name=cb_name, config={})
        self.assertIsNotNone(checkbox)

    def test_keymap(self):
        """tests keymap"""
        checkbox = Checkbox([["Option", "option"]], get_mock_input(), get_mock_output(), name=cb_name, config={})
        self.assertIsNotNone(checkbox.keymap)
        for key_name, callback in checkbox.keymap.items():
            self.assertIsNotNone(callback)

    def test_exit_label_leakage(self):
        """tests whether the exit label of one Checkbox leaks into another"""
        i = get_mock_input()
        o = get_mock_output()
        c1 = Checkbox([["a", "1"]], i, o, name=cb_name + "1", final_button_name="Name1", config={})
        c2 = Checkbox([["b", "2"]], i, o, name=cb_name + "2", final_button_name="Name2", config={})
        c3 = Checkbox([["c", "3"]], i, o, name=cb_name + "3", config={})
        assert (c1.exit_entry != c2.exit_entry)
        assert (c2.exit_entry != c3.exit_entry)
        assert (c1.exit_entry != c3.exit_entry)

    def test_left_key_returns_none(self):
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        cb = Checkbox(contents, get_mock_input(), get_mock_output(), name=cb_name, config={})
        cb.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            cb.deactivate()  # KEY_LEFT
            assert not cb.in_foreground

        with patch.object(cb, 'idle_loop', side_effect=scenario) as p:
            return_value = cb.activate()
        assert return_value is None

        # Checking at the end of the list
        def scenario():
            for i in range(num_elements):
                cb.move_down()  # KEY_DOWN x3
            cb.deactivate()  # KEY_LEFT
            assert not cb.in_foreground

        with patch.object(cb, 'idle_loop', side_effect=scenario) as p:
            return_value = cb.activate()
        assert return_value is None

    def test_graphical_display_redraw(self):
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        self.graphical_display_redraw_runner(contents)

    def test_graphical_display_redraw_with_entries(self):
        num_elements = 3
        contents = [Entry("A" + str(i), name="a" + str(i)) for i in range(num_elements)]
        self.graphical_display_redraw_runner(contents)

    def graphical_display_redraw_runner(self, contents):
        o = get_mock_graphical_output()
        cb = Checkbox(contents, get_mock_input(), o, name=cb_name, config={})
        Canvas.fonts_dir = fonts_dir
        # Exiting immediately, but we should get at least one redraw
        def scenario():
            cb.deactivate()  # KEY_LEFT
            assert not cb.in_foreground

        with patch.object(cb, 'idle_loop', side_effect=scenario) as p:
            return_value = cb.activate()
        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground

    def test_enter_on_last_returns_right(self):
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        self.enter_on_last_returns_right_runner(contents, num_elements)

    def test_enter_on_last_returns_right_with_entries(self):
        num_elements = 3
        contents = [Entry("A" + str(i), name="a" + str(i)) for i in range(num_elements)]
        self.enter_on_last_returns_right_runner(contents, num_elements)

    def enter_on_last_returns_right_runner(self, contents, num_elements):
        cb = Checkbox(contents, get_mock_input(), get_mock_output(), name=cb_name, config={})
        cb.refresh = lambda *args, **kwargs: None

        # Checking at other elements - shouldn't return
        def scenario():
            cb.select_entry()  # KEY_ENTER
            assert cb.in_foreground  # Should still be active
            cb.deactivate()  # because is not deactivated yet and would idle loop otherwise
            assert not cb.in_foreground  # Should no longer be active

        with patch.object(cb, 'idle_loop', side_effect=scenario) as p:
            return_value = cb.activate()
        assert return_value is None

        # Scrolling to the end of the list and pressing Enter - should return a correct dict
        def scenario():
            for i in range(num_elements):
                cb.move_down()  # KEY_DOWN x3
            cb.select_entry()  # KEY_ENTER
            assert not cb.in_foreground

        with patch.object(cb, 'idle_loop', side_effect=scenario) as p:
            return_value = cb.activate()
        assert isinstance(return_value, dict)
        assert all([isinstance(key, basestring) for key in return_value.keys()])
        assert all([isinstance(value, bool) for value in return_value.values()])

    def test_shows_data_on_screen(self):
        """Tests whether the Checkbox outputs data on screen when it's ran"""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        self.shows_data_on_screen_runner(contents)

    def test_shows_data_on_screen_with_entries(self):
        """Tests whether the Checkbox outputs data on screen when it gets entries in the contents"""
        num_elements = 3
        contents = [Entry("A" + str(i), name="a" + str(i)) for i in range(num_elements)]
        self.shows_data_on_screen_runner(contents)

    def shows_data_on_screen_runner(self, contents):
        i = get_mock_input()
        o = get_mock_output()
        cb = Checkbox(contents, i, o, name=cb_name, config={})

        def scenario():
            cb.deactivate()

        with patch.object(cb, 'idle_loop', side_effect=scenario) as p:
            cb.activate()
            #The scenario should only be called once
            assert cb.idle_loop.called
            assert cb.idle_loop.call_count == 1

        assert o.display_data.called
        assert o.display_data.call_count == 1 #One in to_foreground
        assert o.display_data.call_args[0] == (' A0', ' A1', ' A2', ' Accept')


if __name__ == '__main__':
    unittest.main()
