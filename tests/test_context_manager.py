"""tests for Context and ContextManager objects"""
import os
import unittest

from threading import Event
from mock import patch, Mock

try:
    from context_manager import ContextManager, Context, ContextError
except ImportError:
    print("Absolute imports failed, trying relative imports")
    os.sys.path.append(os.path.dirname(os.path.abspath('.')))
    # Store original __import__
    orig_import = __import__

    def import_mock(name, *args, **kwargs):
        if name in ['helpers'] and not kwargs:
            #Have to filter for kwargs since there's a package in 'json'
            #that calls __builtins__.__import__ with keyword arguments
            #and we don't want to mock that call
            return Mock()
        return orig_import(name, *args, **kwargs)

    with patch('__builtin__.__import__', side_effect=import_mock):
        from context_manager import ContextManager, Context, ContextError

class TestContext(unittest.TestCase):
    """tests context class"""
    def test_constructor(self):
        """Tests constructor"""
        c = Context("test_context", lambda *a, **k: True)
        self.assertIsNotNone(c)

    def test_threading(self):
        """Tests whether threaded and non-threaded contexts behave as they should"""
        c = Context("test_context", lambda *a, **k: True)
        e = Event()
        finished = Event()
        c.signal_finished = finished.set
        c.threaded = False # Need to set this flag, otherwise a validation check fails
        c.activate()
        assert(not e.is_set())
        assert(not finished.is_set())
        c.threaded = True
        c.set_target(e.set)
        c.activate()
        finished.wait()
        assert(e.is_set())

    def test_targetless_threaded_context(self):
        """Tests whether a target-less threaded context fails to activate"""
        c = Context("test_context", lambda *a, **k: True)
        try:
            c.activate()
        except ContextError:
            pass
        else:
            raise AssertionError
        # After marking context as non-threaded, it should activate OK
        c.threaded = False
        try:
            c.activate()
        except:
            raise AssertionError
        else:
            pass


class TestContextManager(unittest.TestCase):
    """tests context manager class and interaction between contexts"""
    def test_constructor(self):
        """Tests constructor"""
        cm = ContextManager()
        self.assertIsNotNone(cm)

    def test_initial_contexts(self):
        """Tests whether initial contexts are getting created"""
        cm = ContextManager()
        cm.init_io(Mock(), Mock()) #Implicitly creates initial contexts
        for context_alias, context in cm.contexts.items():
            assert(context_alias in cm.initial_contexts)
            assert(context)

    def test_basic_context_switching(self):
        """Tests whether basic context switching works"""
        cm = ContextManager()
        cm.initial_contexts = [cm.fallback_context, "test1", "test2"]
        cm.init_io(Mock(), Mock())
        assert(cm.current_context is None)
        cm.switch_to_context(cm.fallback_context)
        assert(cm.current_context == cm.fallback_context)
        e1 = Event()
        e2 = Event()
        cm.register_context_target("test1", e1.wait)
        cm.register_context_target("test2", e2.wait)
        cm.switch_to_context("test1")
        assert(cm.current_context == "test1")
        assert(cm.get_previous_context("test1") == cm.fallback_context)
        cm.switch_to_context("test2")
        assert(cm.current_context == "test2")
        assert(cm.get_previous_context("test2") == "test1")
        cm.switch_to_context("test1")
        assert(cm.current_context == "test1")
        assert(cm.get_previous_context("test1") == "test2")
        #Setting events so that threads exit
        e1.set()
        e2.set()

    def test_context_switching_on_context_finish(self):
        """Tests whether basic context switching works"""
        cm = ContextManager()
        cm.init_io(Mock(), Mock())
        cm.switch_to_context(cm.fallback_context)
        e1 = Event()
        c = cm.create_context("test1")
        cm.register_context_target("test1", e1.wait)
        cm.switch_to_context("test1")
        assert(cm.current_context == "test1")
        finished = Event()
        def new_signal_finished():
            c.event_cb(c.name, "finished")
            finished.set()
        with patch.object(c, 'signal_finished', side_effect=new_signal_finished) as p:
            e1.set()
            #Waiting for the thread to exit
            finished.wait()
        assert(cm.current_context == cm.fallback_context)

    def test_targetless_context_switching(self):
        """Tests that switching to a target-less context fails"""
        cm = ContextManager()
        cm.init_io(Mock(), Mock())
        cm.switch_to_context(cm.fallback_context)
        cm.create_context("test1")
        assert(cm.current_context == cm.fallback_context)
        cm.switch_to_context("test1")
        assert(cm.current_context == cm.fallback_context)

    def test_failsafe_fallback_on_io_fail(self):
        cm = ContextManager()
        cm.fallback_context = "m"
        cm.initial_contexts = ["m"]
        cm.init_io(Mock(), Mock())
        cm.switch_to_context(cm.fallback_context)
        c1 = cm.create_context("t1")
        c2 = cm.create_context("t2")
        e1 = Event()
        e2 = Event()
        cm.register_context_target("t1", e1.wait)
        cm.register_context_target("t2", e2.wait)
        cm.switch_to_context("t1")
        # Fucking things up - since context objects are app-accessible,
        # we can't really rely on them staying the same
        del c1.i
        c1.signal_finished = lambda: True
        del c2.i
        # Both current and new contexts are fucked up
        cm.switch_to_context("t2")
        # Setting events so that threads exit
        e1.set()
        e2.set()
        assert(cm.current_context == cm.fallback_context)

    def test_failsafe_fallback_on_thread_fail(self):
        cm = ContextManager()
        cm.fallback_context = "m"
        cm.initial_contexts = ["m"]
        cm.init_io(Mock(), Mock())
        cm.switch_to_context(cm.fallback_context)
        c1 = cm.create_context("t1")
        c2 = cm.create_context("t2")
        e1 = Event()
        e2 = Event()
        cm.register_context_target("t1", e1.wait)
        cm.register_context_target("t2", e2.wait)
        cm.switch_to_context("t1")
        # Removing 
        c1.set_target(None)
        del c1.thread
        c1.signal_finished = lambda: True
        c2.set_target(None)
        # Again, switcing to the fucked up context
        cm.switch_to_context("t2")
        # Setting events so that threads exit
        e1.set()
        e2.set()
        assert(cm.current_context == cm.fallback_context)


if __name__ == '__main__':
    unittest.main()

"""    def test_left_key_exits(self):
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

    def test_keymap_restore_on_resume(self):
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
            assert(r.keymap == keymap2)"""
