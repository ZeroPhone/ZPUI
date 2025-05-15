"""test for Overlays"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import Menu, HelpOverlay, FunctionOverlay, GridMenu, GridMenuLabelOverlay, IntegerAdjustInputOverlay, IntegerAdjustInput, SpinnerOverlay, PurposeOverlay
    from ui.base_list_ui import Canvas
    fonts_dir = "ui/fonts"
except ImportError:
    print("Absolute imports failed, trying relative imports")
    os.sys.path.append(os.path.dirname(os.path.abspath('.')))
    # Store original __import__
    orig_import = __import__

    def import_mock(name, *args):
        if name in ['helpers']:
            # mocking get_all_available_keys
            if args[-1][0] == "get_all_available_keys":
                m = Mock()
                m.get_all_available_keys = Mock(return_value=['KEY_LEFT', 'KEY_RIGHT', 'KEY_UP', 'KEY_DOWN', 'KEY_ENTER'])
                return m
            return Mock()
        elif name == 'ui.utils':
            import utils
            return utils
        return orig_import(name, *args)

    with patch('__builtin__.__import__', side_effect=import_mock):
        from overlays import HelpOverlay, FunctionOverlay, GridMenuLabelOverlay, IntegerAdjustInputOverlay, SpinnerOverlay, PurposeOverlay
        from menu import Menu
        from grid_menu import GridMenu
        from base_list_ui import Canvas
        from number_input import IntegerAdjustInput
        fonts_dir = "../fonts"

def get_mock_input():
    m = Mock()
    m.available_keys = {"driver1":["KEY_LEFT", "KEY_RIGHT", "KEY_UP", "KEY_DOWN", "KEY_ENTER"]}
    return m

def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m

def get_mock_graphical_output(width=128, height=64, mode="1", cw=6, ch=8):
    m = get_mock_output(rows=width//cw, cols=height//ch)
    m.configure_mock(width=width, height=height, device_mode=mode, char_height=ch, char_width=cw, type=["b&w"])
    return m

ui_name = "Overlay test UI element"


class TestOverlays(unittest.TestCase):
    """tests menu class"""

    def test_ho_constructor(self):
        """tests constructor"""
        overlay = HelpOverlay(lambda: True)
        self.assertIsNotNone(overlay)

    def test_ho_apply(self):
        overlay = HelpOverlay(lambda: True)
        mu = Menu([], get_mock_input(), get_mock_output(), name=ui_name, config={})
        overlay.apply_to(mu)
        self.assertIsNotNone(overlay)
        self.assertIsNotNone(mu)

    def test_ho_keymap(self):
        overlay = HelpOverlay(lambda: True)
        mu = Menu([], get_mock_input(), get_mock_output(), name=ui_name, config={})
        overlay.apply_to(mu)
        self.assertIsNotNone(mu.keymap)
        assert("KEY_F5" in mu.keymap)
        assert(all([callable(v) for v in mu.keymap.values()]))

    def test_fo_keymap(self):
        overlay = FunctionOverlay([lambda: True, lambda: False])
        mu = Menu([], get_mock_input(), get_mock_output(), name=ui_name, config={})
        overlay.apply_to(mu)
        self.assertIsNotNone(mu.keymap)
        assert("KEY_F1" in mu.keymap)
        assert("KEY_F2" in mu.keymap)
        assert(all([callable(v) for v in mu.keymap.values()]))

    def test_fo_apply(self):
        overlay = FunctionOverlay([lambda: True, lambda: False])
        mu = Menu([], get_mock_input(), get_mock_output(), name=ui_name, config={})
        overlay.apply_to(mu)
        self.assertIsNotNone(overlay)
        self.assertIsNotNone(mu)

    def test_ho_push_pop_callback(self):
        cb1 = lambda:True
        cb2 = lambda:False
        overlay = HelpOverlay(cb1)
        assert(overlay.get_key_and_callback()[1] == cb1)
        overlay.push_callback(cb2)
        assert(overlay.get_key_and_callback()[1] == cb2)
        overlay.pop_callback()
        assert(overlay.get_key_and_callback()[1] == cb1)

    def test_ho_text_redraw(self):
        overlay = HelpOverlay(lambda: True)
        mu = Menu([["Hello"]], get_mock_input(), get_mock_output(), name=ui_name, config={})
        overlay.apply_to(mu)
        def scenario():
            mu.deactivate()
            assert not mu.in_foreground

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            mu.activate()
        assert mu.o.display_data.called
        assert mu.o.display_data.call_count == 1 #One in to_foreground
        assert mu.o.display_data.call_args[0] == ('Hello', mu.exit_entry[0])

    def test_ho_graphical_redraw(self):
        o = get_mock_graphical_output()
        overlay = HelpOverlay(lambda: True)
        mu = Menu([], get_mock_input(), o, name=ui_name, config={})
        Canvas.fonts_dir = fonts_dir
        overlay.apply_to(mu)
        # Exiting immediately, but we should get at least one redraw
        def scenario():
            mu.deactivate()  # KEY_LEFT
            assert not mu.in_foreground

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            mu.activate()
        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground

    def test_fo_graphical_redraw(self):
        o = get_mock_graphical_output()
        overlay = FunctionOverlay([lambda: True, lambda: False])
        mu = Menu([], get_mock_input(), o, name=ui_name, config={})
        Canvas.fonts_dir = fonts_dir
        overlay.apply_to(mu)
        # Exiting immediately, but we should get at least one redraw
        def scenario():
            mu.deactivate()  # KEY_LEFT
            assert not mu.in_foreground

        with patch.object(mu, 'idle_loop', side_effect=scenario) as p:
            mu.activate()
        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground

    def test_ho_graphical_icon_disappears(self):
        o = get_mock_graphical_output()
        overlay = HelpOverlay(lambda: True)
        mu = Menu([], get_mock_input(), o, name=ui_name, config={})
        mu.idle_loop = lambda *a, **k: True
        Canvas.fonts_dir = fonts_dir
        overlay.apply_to(mu)
        def activate():
            mu.before_activate()
            mu.to_foreground()
            mu.idle_loop()
            img_1 = o.display_image.call_args[0]
            mu.idle_loop()
            mu.refresh()
            img_2 = o.display_image.call_args[0]
            assert(img_1 == img_2)
            for i in range(overlay.duration):
                mu.idle_loop()
            mu.refresh()
            img_2 = o.display_image.call_args[0]
            assert(img_1 != img_2)
            mu.deactivate()  # KEY_LEFT

        with patch.object(mu, 'activate', side_effect=activate) as p:
            mu.activate()

    def test_fo_graphical_icon_disappears(self):
        o = get_mock_graphical_output()
        overlay = FunctionOverlay([lambda: True, lambda: False])
        mu = Menu([], get_mock_input(), o, name=ui_name, config={})
        mu.idle_loop = lambda *a, **k: True
        Canvas.fonts_dir = fonts_dir
        overlay.apply_to(mu)
        def activate():
            mu.before_activate()
            mu.to_foreground()
            mu.idle_loop()
            img_1 = o.display_image.call_args[0]
            mu.idle_loop()
            mu.refresh()
            img_2 = o.display_image.call_args[0]
            assert(img_1 == img_2)
            for i in range(overlay.duration):
                mu.idle_loop()
            mu.refresh()
            img_2 = o.display_image.call_args[0]
            assert(img_1 != img_2)
            mu.deactivate()  # KEY_LEFT

        with patch.object(mu, 'activate', side_effect=activate) as p:
            mu.activate()

    def test_gmlo_apply(self):
        overlay = GridMenuLabelOverlay()
        mu = GridMenu([], get_mock_input(), get_mock_graphical_output(), name=ui_name, config={})
        overlay.apply_to(mu)
        self.assertIsNotNone(overlay)
        self.assertIsNotNone(mu)

    def test_gmlo_graphical_icon_disappears(self):
        o = get_mock_graphical_output()
        overlay = GridMenuLabelOverlay()
        mu = GridMenu([], get_mock_input(), o, name=ui_name, config={})
        mu.idle_loop = lambda *a, **k: True
        Canvas.fonts_dir = fonts_dir
        overlay.apply_to(mu)
        def activate():
            mu.before_activate()
            mu.to_foreground()
            mu.idle_loop()
            img_1 = o.display_image.call_args[0]
            mu.idle_loop()
            mu.refresh()
            img_2 = o.display_image.call_args[0]
            assert(img_1 == img_2)
            for i in range(overlay.duration):
                mu.idle_loop()
            # An internal refresh has happened
            img_2 = o.display_image.call_args[0]
            assert(img_1 != img_2)
            mu.deactivate()  # KEY_LEFT

        with patch.object(mu, 'activate', side_effect=activate) as p:
            mu.activate()

    def test_iaio_apply(self):
        overlay = IntegerAdjustInputOverlay()
        ia = IntegerAdjustInput(0, get_mock_input(), get_mock_output(), name=ui_name)
        overlay.apply_to(ia)
        self.assertIsNotNone(overlay)
        self.assertIsNotNone(ia)

    def test_iaio_number_input(self):
        overlay = IntegerAdjustInputOverlay()
        i = get_mock_input()
        ia = IntegerAdjustInput(0, i, get_mock_output(), name=ui_name)
        overlay.apply_to(ia)

        def scenario():
            keymap = i.set_keymap.call_args[0][0]
            keymap["KEY_1"]()
            assert (ia.number == 1)
            keymap["KEY_2"]()
            assert (ia.number == 12)
            ia.deactivate()
            assert not ia.in_foreground

        with patch.object(ia, 'idle_loop', side_effect=scenario) as p:
            ia.activate()

    def test_so_apply(self):
        overlay = SpinnerOverlay()
        mu = Menu([], get_mock_input(), get_mock_graphical_output(), name=ui_name)
        overlay.apply_to(mu)
        self.assertIsNotNone(overlay)
        self.assertIsNotNone(mu)

    def test_so_spins(self):
        Canvas.fonts_dir = fonts_dir
        o = get_mock_graphical_output()
        overlay = SpinnerOverlay()
        mu = Menu([], get_mock_input(), o, name=ui_name)
        mu.idle_loop = lambda *a, **k: True
        overlay.apply_to(mu)
        overlay.set_state(mu, False)
        def activate():
            mu.before_activate()
            mu.to_foreground()
            mu.idle_loop()
            img_1 = o.display_image.call_args[0]
            mu.idle_loop()
            mu.refresh()
            img_2 = o.display_image.call_args[0]
            assert(img_1 == img_2)
            # enabling the spinner
            overlay.set_state(mu, True)
            # first iteration of the spinner
            mu.idle_loop()
            img_3 = o.display_image.call_args[0]
            assert(img_3 != img_1)
            # second iteration of the spinner
            mu.idle_loop()
            img_4 = o.display_image.call_args[0]
            assert(img_4 != img_1)
            assert(img_4 != img_3)
            # disabling the spinner
            overlay.set_state(mu, False)
            mu.idle_loop() # now idle_loop shouldn't contain a refresh
            img_5 = o.display_image.call_args[0]
            assert(img_5 == img_4)
            mu.refresh() # now, after an explicit refresh, there should be no spinner left
            img_6 = o.display_image.call_args[0]
            assert(img_6 == img_1)
            assert(img_6 != img_3)
            assert(img_6 != img_4)
            mu.deactivate()  # KEY_LEFT

        with patch.object(mu, 'activate', side_effect=activate) as p:
            mu.activate()

    def test_po_apply(self):
        overlay = PurposeOverlay()
        mu = Menu([], get_mock_input(), get_mock_graphical_output(), name=ui_name)
        overlay.apply_to(mu)
        self.assertIsNotNone(overlay)
        self.assertIsNotNone(mu)

    def test_po_purpose_disappears(self):
        o = get_mock_graphical_output()
        overlay = PurposeOverlay()
        mu = Menu([], get_mock_input(), o, name=ui_name)
        self.assertIsNotNone(overlay)
        self.assertIsNotNone(mu)
        Canvas.fonts_dir = fonts_dir
        overlay.apply_to(mu)
        def activate():
            mu.before_activate()
            mu.to_foreground()
            img_1 = o.display_image.call_args[0]
            mu.refresh()
            img_2 = o.display_image.call_args[0]
            assert(img_1 == img_2)
            mu.keymap["KEY_ENTER"]()
            img_2 = o.display_image.call_args[0]
            assert(img_1 != img_2)
            mu.deactivate()

        with patch.object(mu, 'activate', side_effect=activate) as p:
            mu.activate()

if __name__ == '__main__':
    unittest.main()
