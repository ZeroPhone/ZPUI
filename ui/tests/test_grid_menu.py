"""test for GridMenu"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import GridMenu, Canvas
    fonts_dir = "ui/fonts"
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
            from grid_menu import GridMenu
    else:
        with patch('__builtin__.__import__', side_effect=import_mock):
            import canvas
            canvas.fonts_dir = "../fonts/"
            Canvas = canvas.Canvas
            expand_coords = canvas.expand_coords
            from grid_menu import GridMenu

def get_mock_input():
    return Mock()

def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m

def get_mock_graphical_output(width=128, height=64, mode="1", cw=6, ch=8):
    m = get_mock_output(rows=width/cw, cols=height/ch)
    m.configure_mock(width=width, height=height, device_mode=mode, char_height=ch, char_width=cw, type=["b&w"] if not mode.startswith("RGB") else ["b&w", "color"])
    return m


mu_name = "Test GridMenu"

class TestGridMenu(unittest.TestCase):
    """tests GridMenu class"""

    def test_constructor(self):
        """tests constructor"""
        menu = GridMenu([["Option", "option"]], get_mock_input(), get_mock_graphical_output(), name=mu_name, config={})
        self.assertIsNotNone(menu)

    def test_keymap(self):
        """tests keymap"""
        menu = GridMenu([["Option", "option"]], get_mock_input(), get_mock_graphical_output(), name=mu_name, config={})
        self.assertIsNotNone(menu.keymap)
        for key_name, callback in menu.keymap.items():
            self.assertIsNotNone(callback)

    def test_exit_label_leakage(self):
        """tests whether the exit label of one GridMenu leaks into another"""
        i = get_mock_input()
        o = get_mock_graphical_output()
        c1 = GridMenu([["a", "1"]], i, o, name=mu_name + "1", config={})
        c1.exit_entry = ["Restart ZPUI", "exit"]
        c2 = GridMenu([["b", "2"]], i, o, name=mu_name + "2", config={})
        c2.exit_entry = ["Do not restart ZPUI", "exit"]
        c3 = GridMenu([["c", "3"]], i, o, name=mu_name + "3", config={})
        assert (c1.exit_entry != c2.exit_entry)
        assert (c2.exit_entry != c3.exit_entry)
        assert (c1.exit_entry != c3.exit_entry)

    @unittest.skip("LEFT is used for navigation")
    def test_left_key_disabled_when_not_exitable(self):
        """Tests whether a menu does not exit on KEY_LEFT when exitable is set to False"""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        mu = GridMenu(contents, get_mock_input(), get_mock_graphical_output(), name=mu_name, exitable=False, config={})
        mu.refresh = lambda *args, **kwargs: None

        def scenario():
            assert "KEY_LEFT" not in mu.keymap
            mu.deactivate()
            assert not mu.is_active

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            mu.activate()

    @unittest.skip("LEFT is used for navigation")
    def test_left_key_returns_none(self):
        """ A GridMenu is never supposed to return anything other than None"""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        mu = GridMenu(contents, get_mock_input(), get_mock_graphical_output(), name=mu_name, config={})
        mu.refresh = lambda *args, **kwargs: None

        # Checking at the start of the list
        def scenario():
            mu.deactivate()  # KEY_LEFT
            assert not mu.is_active

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            return_value = mu.activate()
        assert return_value is None

        # Checking at the end of the list
        def scenario():
            for i in range(num_elements):
                mu.move_down()  # KEY_DOWN x3
            mu.deactivate()  # KEY_LEFT
            assert not mu.is_active

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            return_value = mu.activate()
        assert return_value is None

    def test_graphical_display_redraw(self):
        num_elements = 1
        o = get_mock_graphical_output()
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        mu = GridMenu(contents, get_mock_input(), o, name=mu_name, config={})
        Canvas.fonts_dir = fonts_dir
        # Exiting immediately, but we should get at least one redraw
        def scenario():
            mu.deactivate()  # KEY_LEFT
            assert not mu.is_active

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            return_value = mu.activate()
        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground

    @unittest.skip("needs to check whether the callback is executed instead")
    def test_enter_on_last_returns_right(self):
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        mu = GridMenu(contents, get_mock_input(), get_mock_graphical_output(), name=mu_name, config={})
        mu.refresh = lambda *args, **kwargs: None

        # Checking at other elements - shouldn't return
        def scenario():
            mu.select_entry()  # KEY_ENTER
            assert mu.is_active  # Should still be active
            mu.deactivate()  # because is not deactivated yet and would idle loop otherwise

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            return_value = mu.activate()
        assert return_value is None

        # Scrolling to the end of the list and pressing Enter - should return a correct dict
        def scenario():
            for i in range(num_elements):
                mu.move_down()  # KEY_DOWN x3
            mu.select_entry()  # KEY_ENTER
            assert not mu.is_active

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            return_value = mu.activate()
        assert isinstance(return_value, dict)
        assert all([isinstance(key, basestring) for key in return_value.keys()])
        assert all([isinstance(value, bool) for value in return_value.values()])

    def test_shows_data_on_128x64_screen(self):
        """Tests whether the GridMenu outputs data on screen when it's ran"""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        i = get_mock_input()
        o = get_mock_graphical_output()
        mu = GridMenu(contents, i, o, name=mu_name, config={})

        def scenario():
            mu.deactivate()

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            mu.activate()
            #The scenario should only be called once
            assert mu.idle_loop.called
            assert mu.idle_loop.call_count == 1

        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground

    def test_shows_data_on_400x240_screen(self):
        """Tests whether the GridMenu outputs data on a 400x240 screen when it's ran. covers BebbleGridView."""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        i = get_mock_input()
        o = get_mock_graphical_output(width=400, height=240)
        mu = GridMenu(contents, i, o, name=mu_name, config={})

        def scenario():
            mu.deactivate()

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            mu.activate()
            #The scenario should only be called once
            assert mu.idle_loop.called
            assert mu.idle_loop.call_count == 1

        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground

    def test_shows_data_on_400x240_color_screen(self):
        """Tests whether the GridMenu outputs data on a 400x240 screen when it's ran. covers BebbleGridView."""
        num_elements = 3
        contents = [["A" + str(i), "a" + str(i)] for i in range(num_elements)]
        i = get_mock_input()
        o = get_mock_graphical_output(width=400, height=240, mode="RGB")
        mu = GridMenu(contents, i, o, name=mu_name, config={})

        def scenario():
            mu.deactivate()

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            mu.activate()
            #The scenario should only be called once
            assert mu.idle_loop.called
            assert mu.idle_loop.call_count == 1

        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground


if __name__ == '__main__':
    unittest.main()
