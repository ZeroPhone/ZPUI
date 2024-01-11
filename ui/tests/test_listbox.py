"""test for Listbox"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import Listbox, Entry
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
        from listbox import Listbox
        from entry import Entry
        from base_list_ui import Canvas
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

lb_name = "Test Listbox"


class TestListbox(unittest.TestCase):
    """tests Listbox class"""

    def test_constructor(self):
        """tests constructor"""
        lb = Listbox([["Option", "option"]], get_mock_input(), get_mock_output(), name=lb_name, config={})
        self.assertIsNotNone(lb)

    def test_keymap(self):
        """tests keymap"""
        lb = Listbox([["Option", "option"]], get_mock_input(), get_mock_output(), name=lb_name, config={})
        self.assertIsNotNone(lb.keymap)
        for key_name, callback in lb.keymap.items():
            self.assertIsNotNone(callback)

    def test_contents(self):
        """tests contents str-to-list replacement"""
        lb = Listbox([["Option", "option1"], "option2"], get_mock_input(), get_mock_output(), name=lb_name, config={})
        self.assertIsNotNone(lb.contents)
        for entry in lb.contents:
            assert(isinstance(entry, list))

    @unittest.skip("expected to fail since Listbox doesn't handle exit label replacement yet")
    def test_exit_label_leakage(self):
        """tests whether the exit label of one Listbox leaks into another"""
        i = get_mock_input()
        o = get_mock_output()
        c1 = Listbox([["a", "1"]], i, o, name=lb_name + "1", final_button_name="Name1", config={})
        c2 = Listbox([["b", "2"]], i, o, name=lb_name + "2", final_button_name="Name2", config={})
        c3 = Listbox([["c", "3"]], i, o, name=lb_name + "3", config={})
        assert (c1.exit_entry != c2.exit_entry)
        assert (c2.exit_entry != c3.exit_entry)
        assert (c1.exit_entry != c3.exit_entry)

    def test_left_key_works_when_not_exitable(self):
        """Listbox should still exit on KEY_LEFT when exitable is set to False"""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        lb = Listbox(contents, get_mock_input(), get_mock_output(), name=lb_name, config={})
        lb.refresh = lambda *args, **kwargs: None

        def scenario():
            assert "KEY_LEFT" in lb.keymap
            lb.deactivate()
            assert not lb.in_foreground

        with patch.object(lb, 'idle_loop', side_effect=scenario) as p:
            lb.activate()

    def test_left_key_returns_none(self):
        """ A Listbox shouldn't return anything when LEFT is pressed"""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        lb = Listbox(contents, get_mock_input(), get_mock_output(), name=lb_name, config={})
        lb.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            lb.deactivate()  # KEY_LEFT
            assert not lb.in_foreground

        with patch.object(lb, 'idle_loop', side_effect=scenario) as p:
            return_value = lb.activate()
        assert return_value is None

        # Checking at the end of the list
        def scenario():
            for i in range(num_elements):
                lb.move_down()  # KEY_DOWN x3
            lb.deactivate()  # KEY_LEFT
            assert not lb.in_foreground

        with patch.object(lb, 'idle_loop', side_effect=scenario) as p:
            return_value = lb.activate()
        assert return_value is None

    def test_returns_on_enter(self):
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        self.returns_on_enter_runner(contents, num_elements, contents[0][1], contents[-1][1])

    def test_returns_on_enter_entry(self):
        num_elements = 3
        contents = [Entry("A" + str(i), name="a" + str(i)) for i in range(num_elements)]
        self.returns_on_enter_runner(contents, num_elements, contents[0].name, contents[-1].name)

    def returns_on_enter_runner(self, contents, num_elements, exp_return1, exp_return2):
        lb = Listbox(contents, get_mock_input(), get_mock_output(), name=lb_name, config={})
        lb.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            lb.select_entry()  # KEY_ENTER
            assert not lb.in_foreground

        with patch.object(lb, 'idle_loop', side_effect=scenario) as p:
            return_value = lb.activate()
        assert return_value == exp_return1

        # Checking at the end of the list
        def scenario():
            for i in range(num_elements-1):
                lb.move_down()  # KEY_DOWN x2
            lb.select_entry()  # KEY_ENTER
            assert not lb.in_foreground

        with patch.object(lb, 'idle_loop', side_effect=scenario) as p:
            return_value = lb.activate()
        assert return_value == exp_return2

    def test_selected(self):
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        selected = contents[1][1]
        self.selected_runner(contents, selected)

    def test_selected_entry(self):
        num_elements = 3
        contents = [Entry("A" + str(i), name="a" + str(i)) for i in range(num_elements)]
        selected = contents[1].name
        self.selected_runner(contents, selected)

    def selected_runner(self, contents, selected):
        lb = Listbox(contents, get_mock_input(), get_mock_output(), selected=selected, name=lb_name, config={})
        lb.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            lb.select_entry()  # KEY_ENTER
            assert not lb.in_foreground

        with patch.object(lb, 'idle_loop', side_effect=scenario) as p:
            return_value = lb.activate()
        assert return_value == selected

    def test_selected_single_el(self):
        num_elements = 3
        contents = [["A" + str(i)] for i in range(num_elements)]
        selected = contents[1][0]
        self.selected_single_el_entry_runner(contents, selected)

    def test_selected_single_el_entry(self):
        num_elements = 3
        contents = [Entry("A" + str(i)) for i in range(num_elements)]
        selected = contents[1].text
        self.selected_single_el_entry_runner(contents, selected)

    def selected_single_el_entry_runner(self, contents, selected):
        lb = Listbox(contents, get_mock_input(), get_mock_output(), selected=selected, name=lb_name, config={})
        lb.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            lb.select_entry()  # KEY_ENTER
            assert not lb.in_foreground

        with patch.object(lb, 'idle_loop', side_effect=scenario) as p:
            return_value = lb.activate()
        assert return_value == selected

    def test_graphical_display_redraw(self):
        num_elements = 2
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        self.graphical_display_redraw_runner(contents)

    def test_graphical_display_redraw_with_entries(self):
        num_elements = 2
        contents = [Entry("A" + str(i), name="a" + str(i)) for i in range(num_elements)]
        self.graphical_display_redraw_runner(contents)

    def graphical_display_redraw_runner(self, contents):
        o = get_mock_graphical_output()
        lb = Listbox(contents, get_mock_input(), o, name=lb_name, config={})
        Canvas.fonts_dir = fonts_dir
        # Exiting immediately, but we should get at least one redraw
        def scenario():
            lb.deactivate()  # KEY_LEFT
            assert not lb.in_foreground

        with patch.object(lb, 'idle_loop', side_effect=scenario) as p:
            return_value = lb.activate()
        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground

    def test_shows_data_on_screen(self):
        """Tests whether the Listbox outputs data on screen when it's ran"""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        self.shows_data_on_screen_runner(contents)

    def test_shows_data_on_screen_with_entries(self):
        """Tests whether the Listbox outputs data on screen when it's ran - using entries"""
        num_elements = 3
        contents = [Entry("A" + str(i), name="a" + str(i)) for i in range(num_elements)]
        self.shows_data_on_screen_runner(contents)

    def shows_data_on_screen_runner(self, contents):
        i = get_mock_input()
        o = get_mock_output()
        lb = Listbox(contents, i, o, name=lb_name, config={})

        def scenario():
            lb.deactivate()

        with patch.object(lb, 'idle_loop', side_effect=scenario) as p:
            lb.activate()
            #The scenario should only be called once
            assert lb.idle_loop.called
            assert lb.idle_loop.call_count == 1

        assert o.display_data.called
        assert o.display_data.call_count == 1 #One in to_foreground
        assert o.display_data.call_args[0] == ('A0', 'A1', 'A2', lb.exit_entry[0])

if __name__ == '__main__':
    unittest.main()
