"""tests for Refresher"""
import os
import unittest

from mock import patch, Mock

from PIL import Image

try:
    from ui import Refresher, RefresherExitException, RefresherView
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
        from refresher import Refresher, RefresherExitException, RefresherView


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

r_name = "Test Refresher"


class TestRefresher(unittest.TestCase):
    """Tests the Refresher class"""

    def test_constructor(self):
        """Tests constructor"""
        r = Refresher(lambda: "Hello", get_mock_input(), get_mock_output(), name=r_name)
        self.assertIsNotNone(r)

    def test_keymap(self):
        """Tests the keymap entries"""
        r = Refresher(lambda: "Hello", get_mock_input(), get_mock_output(), name=r_name)
        self.assertIsNotNone(r.keymap)
        for key_name, callback in r.keymap.items():
            self.assertIsNotNone(callback)

    def test_string_keymap(self):
        """Tests the keymap entries"""
        k = {"KEY_LEFT":'refresh', "KEY_RIGHT":'deactivate'}
        r = Refresher(lambda: "Hello", get_mock_input(), get_mock_output(), keymap=k, name=r_name)
        for key_name, callback in r.keymap.items():
            self.assertIsNotNone(callback)
        assert (r.keymap["KEY_LEFT"] == r.refresh)
        assert (r.keymap["KEY_RIGHT"] == r.deactivate)

    def test_exit_label_leakage(self):
        """tests whether the keymaps (and keymap entries) of different Refresher leak one into another"""
        i = get_mock_input()
        o = get_mock_output()
        r1 = Refresher(lambda: "Hello", i, o, name=r_name + "1", keymap={"KEY_LEFT":lambda: True})
        r2 = Refresher(lambda: "Hello", i, o, name=r_name + "2", keymap={"KEY_LEFT":lambda: False})
        r3 = Refresher(lambda: "Hello", i, o, name=r_name + "3")
        assert (r1.keymap != r2.keymap)
        assert (r1.keymap["KEY_LEFT"] != r2.keymap["KEY_LEFT"])
        assert (r2.keymap != r3.keymap)
        assert (r2.keymap["KEY_LEFT"] != r3.keymap["KEY_LEFT"])
        assert (r1.keymap != r3.keymap)
        assert (r1.keymap["KEY_LEFT"] != r3.keymap["KEY_LEFT"])

    def test_left_key_exits(self):
        r = Refresher(lambda: "Hello", get_mock_input(), get_mock_output(), name=r_name)
        r.refresh = lambda *args, **kwargs: None

        # This test doesn't actually test whether the Refresher exits
        # It only tests whether the in_foreground attribute is set
        # Any ideas? Maybe use some kind of "timeout" library?
        def scenario():
            r.keymap["KEY_LEFT"]()
            assert not r.in_foreground
            # If the test fails, either the assert will trigger a test failure,
            # or the idle loop will just run indefinitely
            # The exception thrown should protect from the latter
            raise KeyboardInterrupt

        with patch.object(r, 'idle_loop', side_effect=scenario) as p:
            try:
                r.activate()
            except KeyboardInterrupt:
                pass #Test succeeded

    def test_shows_data_on_screen(self):
        """Tests whether the Refresher outputs data on screen when it's ran"""
        i = get_mock_input()
        o = get_mock_output()
        r = Refresher(lambda: "Hello", i, o, name=r_name)

        def scenario():
            r.refresh()
            r.deactivate()

        with patch.object(r, 'idle_loop', side_effect=scenario) as p:
            r.activate()
            #The scenario should only be called once
            assert r.idle_loop.called
            assert r.idle_loop.call_count == 1

        assert o.display_data.called
        assert o.display_data.call_count == 2 #One in to_foreground, and one in patched idle_loop
        assert o.display_data.call_args_list[0][0] == ("Hello", )
        assert o.display_data.call_args_list[1][0] == ("Hello", )

    def test_pause_resume(self):
        """Tests whether the Refresher stops outputting data on the screen when it's paused,
        and resumes outputting data on the screen when resumed."""
        i = get_mock_input()
        o = get_mock_output()
        r = Refresher(lambda: "Hello", i, o, name=r_name, refresh_interval=0.1)
        #refresh_interval is 0.1 so that _counter always stays 0
        #and idle_loop always refreshes

        #Doing what an activate() would do, but without a loop
        r.to_foreground()
        assert o.display_data.called
        assert o.display_data.call_count == 1 #to_foreground calls refresh()
        r.idle_loop()
        assert o.display_data.call_count == 2 #not paused
        r.pause()
        r.idle_loop()
        assert o.display_data.call_count == 2 #paused, so count shouldn't change
        r.resume()
        assert o.display_data.call_count == 3 #resume() refreshes the display
        r.idle_loop()
        assert o.display_data.call_count == 4 #should be refresh the display normally now

    def test_refresher_exit_exception(self):
        """
        Tests whether the Refresher deactivates when it receives an exit exception.
        """
        i = get_mock_input()
        o = get_mock_output()
        def get_data():
            raise RefresherExitException
        r = Refresher(get_data, i, o, name=r_name, refresh_interval=0.1)

        #Doing what an activate() would do, but without a loop
        r.to_foreground()
        #Should've caught the exception and exited, since to_foreground() calls refresh()
        assert r.in_foreground == False

    def test_keymap_restore_on_resume(self):
        """Tests whether the Refresher re-sets the keymap upon resume."""
        i = get_mock_input()
        o = get_mock_output()
        r = Refresher(lambda: "Hello", i, o, name=r_name, refresh_interval=0.1)
        r.refresh = lambda *args, **kwargs: None

        r.to_foreground()
        assert i.set_keymap.called
        assert i.set_keymap.call_count == 1
        assert i.set_keymap.call_args[0][0] == r.keymap
        assert "KEY_LEFT" in r.keymap
        r.pause()
        assert i.set_keymap.call_count == 1 #paused, so count shouldn't change
        i.set_keymap(None)
        assert i.set_keymap.call_args[0][0] != r.keymap
        r.resume()
        assert i.set_keymap.call_count == 3 #one explicitly done in the test right beforehand
        assert i.set_keymap.call_args[0][0] == r.keymap

    def test_set_interval(self):
        """
        Tests whether the refresh_interval of Refresher is set correctly
        when using set_refresh_interval.
        """
        i = get_mock_input()
        o = get_mock_output()
        r = Refresher(lambda: "Hello", i, o, name=r_name, refresh_interval=1)

        assert(r.refresh_interval == 1)
        assert(r.sleep_time == 0.1)
        assert(r.iterations_before_refresh == 10)
        # Refresh intervals up until 0.1 don't change the sleep time
        r.set_refresh_interval(0.1)
        assert(r.refresh_interval == 0.1)
        assert(r.sleep_time == 0.1)
        assert(r.iterations_before_refresh == 1)
        # Refresh intervals less than 0.1 change sleep_time to match refresh interval
        r.set_refresh_interval(0.01)
        assert(r.refresh_interval == 0.01)
        assert(r.sleep_time == 0.01)
        assert(r.iterations_before_refresh == 1)
        # Now setting refresh_interval to a high value
        r.set_refresh_interval(10)
        assert(r.refresh_interval == 10)
        assert(r.sleep_time == 0.1) # Back to normal
        assert(r.iterations_before_refresh == 100)

    def test_update_keymap(self):
        """Tests whether the Refresher updates the keymap correctly."""
        i = get_mock_input()
        o = get_mock_output()
        r = Refresher(lambda: "Hello", i, o, name=r_name, refresh_interval=0.1)
        r.refresh = lambda *args, **kwargs: None

        # We need to patch "process_callback" because otherwise the keymap callbacks
        # are wrapped and we can't test equivalence
        with patch.object(r, 'process_callback', side_effect=lambda keymap:keymap) as p:
            keymap1 = {"KEY_LEFT": lambda:1}
            r.update_keymap(keymap1)
            assert(r.keymap == keymap1)
            keymap2 = {"KEY_RIGHT": lambda:2}
            r.update_keymap(keymap2)
            keymap2.update(keymap1)
            assert(r.keymap == keymap2)

    def test_refresher_view(self):
        text_cb = Mock()
        text_cb.return_value = "Test"
        monochrome_cb = Mock()
        monochrome_cb.return_value = Image.new("1", (128, 64))
        color_cb = Mock()
        color_cb.return_value = Image.new("RGB", (128, 64))
        view = RefresherView(text_cb, monochrome_cb, color_cb)
        i = get_mock_input()
        o = get_mock_output()
        r = Refresher(view, i, o)
        r.to_foreground()
        r.refresh()
        assert(text_cb.called)
        assert(o.display_data.called)
        assert(o.display_data.call_count == 2)
        o = get_mock_graphical_output()
        r = Refresher(view, i, o)
        r.to_foreground()
        r.refresh()
        assert(monochrome_cb.called)
        assert(o.display_image.called)
        assert(o.display_image.call_count == 2)
        o.type.append("color")
        r = Refresher(view, i, o)
        r.to_foreground()
        r.refresh()
        assert(color_cb.called)
        assert(o.display_image.called)
        assert(o.display_image.call_count == 4)

if __name__ == '__main__':
    unittest.main()
