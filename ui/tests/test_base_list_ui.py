"""test for BaseListUIElement"""
import os
import unittest

from mock import patch, Mock

try:
    from ui.base_list_ui import BaseListUIElement, Canvas
    from ui import Entry
    fonts_dir = "ui/fonts"
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
        from base_list_ui import Canvas, BaseListUIElement
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

el_name = "Test BaseListUIElement"


class TestBaseListUIElement(unittest.TestCase):
    """tests base list ui element class"""

    def test_constructor(self):
        """tests constructor"""
        element = BaseListUIElement([["Option", "option"]], get_mock_input(), get_mock_output(), name=el_name, config={})
        self.assertIsNotNone(element)

    def test_keymap(self):
        """tests keymap"""
        element = BaseListUIElement([["Option", "option"]], get_mock_input(), get_mock_output(), name=el_name, config={})
        self.assertIsNotNone(element.keymap)
        for key_name, callback in element.keymap.items():
            self.assertIsNotNone(callback)

    def test_properties(self):
        """tests in_background property"""
        element = BaseListUIElement([["Option", "option"]], get_mock_input(), get_mock_output(), name=el_name, config={})
        assert(element.in_background == False)
        assert(not element._in_background.is_set())
        element.in_background = True
        assert(element.in_background == True)
        assert(element._in_background.is_set())

    @unittest.skip("different exit label functionality not yet implemented")
    def test_exit_label_leakage(self):
        """tests whether the exit label of one BaseListUIElement leaks into another"""
        i = get_mock_input()
        o = get_mock_output()
        c1 = BaseListUIElement([["a", "1"]], i, o, name=el_name + "1", final_button_name="Name1", config={})
        c2 = BaseListUIElement([["b", "2"]], i, o, name=el_name + "2", final_button_name="Name2", config={})
        c3 = BaseListUIElement([["c", "3"]], i, o, name=el_name + "3", config={})
        assert (c1.exit_entry != c2.exit_entry)
        assert (c2.exit_entry != c3.exit_entry)
        assert (c1.exit_entry != c3.exit_entry)

    def test_left_key_returns_none(self):
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        el = BaseListUIElement(contents, get_mock_input(), get_mock_output(), name=el_name, config={})
        el.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            el.deactivate()  # KEY_LEFT
            assert not el.is_active

        with patch.object(el, 'idle_loop', side_effect=scenario) as p:
            return_value = el.activate()
        assert return_value is None

        # Checking at the end of the list
        def scenario():
            for i in range(num_elements):
                el.move_down()  # KEY_DOWN x3
            el.deactivate()  # KEY_LEFT
            assert not el.is_active

        with patch.object(el, 'idle_loop', side_effect=scenario) as p:
            return_value = el.activate()
        assert return_value is None

    def test_graphical_display_redraw(self):
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        self.graphical_display_redraw_runner(contents)

    def test_graphical_display_entry_redraw(self):
        num_elements = 3
        contents = [Entry("A" + str(i), name="a" + str(i)) for i in range(num_elements)]
        self.graphical_display_redraw_runner(contents)

    def graphical_display_redraw_runner(self, contents):
        o = get_mock_graphical_output()
        el = BaseListUIElement(contents, get_mock_input(), o, name=el_name, config={})
        Canvas.fonts_dir = fonts_dir
        # Exiting immediately, but we should get at least one redraw
        def scenario():
            el.deactivate()  # KEY_LEFT
            assert not el.is_active

        with patch.object(el, 'idle_loop', side_effect=scenario) as p:
            el.activate()
        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground

    @unittest.skip("baselistuielement does not return anything; needs to be something other")
    def test_enter_on_last_returns_right(self):
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        el = BaseListUIElement(contents, get_mock_input(), get_mock_output(), name=el_name, config={})
        el.refresh = lambda *args, **kwargs: None

        # Checking at other elements - shouldn't return
        def scenario():
            el.select_entry()  # KEY_ENTER
            assert el.is_active  # Should still be active
            el.deactivate()  # because is not deactivated yet and would idle loop otherwise

        with patch.object(el, 'idle_loop', side_effect=scenario) as p:
            return_value = el.activate()
        assert return_value is None

        # Scrolling to the end of the list and pressing Enter - should return a correct dict
        def scenario():
            for i in range(num_elements):
                el.move_down()  # KEY_DOWN x3
            el.select_entry()  # KEY_ENTER
            assert not el.is_active

        with patch.object(el, 'idle_loop', side_effect=scenario) as p:
            return_value = el.activate()
        assert isinstance(return_value, dict)
        assert all([isinstance(key, basestring) for key in return_value.keys()])
        assert all([isinstance(value, bool) for value in return_value.values()])

    def test_shows_data_on_screen(self):
        """Tests whether the BaseListUIElement outputs data on screen when it's ran"""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        self.shows_data_on_screen_runner(contents)

    def test_entry_shows_data_on_screen(self):
        """Tests whether the BaseListUIElement outputs data on screen when it's ran"""
        num_elements = 3
        contents = [Entry("A" + str(i), name="a" + str(i)) for i in range(num_elements)]
        self.shows_data_on_screen_runner(contents)

    def shows_data_on_screen_runner(self, contents):
        i = get_mock_input()
        o = get_mock_output()
        el = BaseListUIElement(contents, i, o, name=el_name, config={})

        def scenario():
            el.deactivate()
            assert not el.is_active

        with patch.object(el, 'idle_loop', side_effect=scenario) as p:
            el.activate()
            #The scenario should only be called once
            assert el.idle_loop.called
            assert el.idle_loop.call_count == 1

        assert o.display_data.called
        assert o.display_data.call_count == 1 #One in to_foreground
        assert o.display_data.call_args[0] == ('A0', 'A1', 'A2', 'Back')

    def test_pagedown_pageup_refresh_once(self):
        """Tests whether the BaseListUIElement page_down and page_up only refresh the screen once."""
        num_elements = 20
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        i = get_mock_input()
        o = get_mock_output()
        el = BaseListUIElement(contents, i, o, name=el_name, config={})

        def scenario():
            assert o.display_data.call_count == 1 #One in to_foreground
            el.page_down()
            assert o.display_data.call_count == 2 #One more
            el.page_up()
            assert o.display_data.call_count == 3 #And one more
            el.deactivate()
            assert not el.is_active

        with patch.object(el, 'idle_loop', side_effect=scenario) as p:
            el.activate()

    def test_append_exit_works(self):
        """
        Tests whether the BaseListUIElement stops appending "Exit" when append_exit
        is set to false.
        """
        contents = [["A" + str(i), "a" + str(i)] for i in range(3)]
        i = get_mock_input()
        o = get_mock_output()
        el = BaseListUIElement(contents, i, o, name=el_name, append_exit=False, config={})

        def scenario():
            el.deactivate()
            assert not el.is_active

        with patch.object(el, 'idle_loop', side_effect=scenario) as p:
            el.activate()

        assert o.display_data.call_args[0] == ('A0', 'A1', 'A2')

    def test_content_update_maintains_pointers(self):
        """Tests whether the BaseListUIElement outputs data on screen when it's ran"""
        i = get_mock_input()
        o = get_mock_output()

        contents = [["A" + str(x), "a" + str(x)] for x in range(10)]
        el = BaseListUIElement(contents, i, o, name=el_name, config={})

        def scenario():
            for x in range(5):
                el.move_down()

            # Now, we should be on element "A3"
            assert o.display_data.called
            assert o.display_data.call_count == 6 # 1 in to_foreground, 5 in move_down
            assert o.display_data.call_args[0] == ('A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7')

            # Setting shorter contents and scrolling some more
            el.set_contents([["A" + str(x), "a" + str(x)] for x in range(3)])
            el.move_up()
            for x in range(3):
                el.move_down()
            assert o.display_data.call_count == 6 + 4 # 1 in move_up, 3 in move_down
            assert o.display_data.call_args[0] == ('A0', 'A1', 'A2', 'Back')

            el.deactivate()
            assert not el.is_active

        with patch.object(el, 'idle_loop', side_effect=scenario) as p:
            el.activate()


if __name__ == '__main__':
    unittest.main()
