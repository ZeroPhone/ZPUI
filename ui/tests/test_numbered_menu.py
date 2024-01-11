"""test for NumberedMenu"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import NumberedMenu
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
        from numbered_menu import NumberedMenu

def get_mock_input():
    return Mock()


def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m


def build_contents(num_elements=3):
    return [["A" + str(i), lambda x=i: x] for i in range(num_elements)]

nm_name = "Test NumberedMenu"


class TestNumberedMenu(unittest.TestCase):
    """tests dialog box class"""

    def test_constructor(self):
        """tests constructor"""
        nm = NumberedMenu(build_contents(), get_mock_input(), get_mock_output(), name=nm_name, config={})
        self.assertIsNotNone(nm)

    def test_keymap(self):
        """tests keymap"""
        nm = NumberedMenu(build_contents(), get_mock_input(), get_mock_output(), name=nm_name, config={})
        self.assertIsNotNone(nm.keymap)
        for key_name, callback in nm.keymap.items():
            self.assertIsNotNone(callback)

    @unittest.skip("need to implement the corresponding mechanism")
    def test_exit_label_leakage(self):
        """tests whether the exit label of one NumberedMenu leaks into another"""
        i = get_mock_input()
        o = get_mock_output()
        m1 = NumberedMenu(build_contents(), i, o, name=nm_name + "1", config={})
        m2 = NumberedMenu(build_contents(), i, o, name=nm_name + "2", config={})
        m3 = NumberedMenu(build_contents(), i, o, name=nm_name + "3", config={})
        m1.exit_entry = [["Refresh", lambda: None]]
        m2.exit_entry[0] = "Exit"
        assert (m1.exit_entry != m2.exit_entry)
        assert (m2.exit_entry != m3.exit_entry)
        assert (m1.exit_entry != m3.exit_entry)

    def test_key_left_exits_returns_none(self):
        nm = NumberedMenu(build_contents(), get_mock_input(), get_mock_output(), name=nm_name, config={})

        def scenario():
            nm.deactivate()
            assert not nm.in_foreground

        with patch.object(nm, 'idle_loop', side_effect=scenario) as p:
            nm.activate()

    def test_shows_data_on_screen(self):
        """Tests whether the NumberedMenu outputs data on screen when it's ran"""
        nm = NumberedMenu(build_contents(3), get_mock_input(), get_mock_output(), name=nm_name, config={})

        def scenario():
            nm.deactivate()

        with patch.object(nm, 'idle_loop', side_effect=scenario) as p:
            nm.activate()
            #The scenario should only be called once
            assert nm.idle_loop.called
            assert nm.idle_loop.call_count == 1

        assert nm.o.display_data.called
        assert nm.o.display_data.call_count == 1 #One in to_foreground
        assert nm.o.display_data.call_args[0] == ('0 A0', '1 A1', '2 A2', '3 {}'.format(nm.exit_entry[0]))

    def test_no_prepend_numbers(self):
        """Tests whether the NumberedMenu stops prepending numbers when it gets
        the corresponding argument"""
        nm = NumberedMenu(build_contents(3), get_mock_input(), get_mock_output(), prepend_numbers=False, name=nm_name, config={})

        def scenario():
            nm.deactivate()

        with patch.object(nm, 'idle_loop', side_effect=scenario) as p:
            nm.activate()

        assert nm.o.display_data.called
        assert nm.o.display_data.call_count == 1 #One in to_foreground
        assert nm.o.display_data.call_args[0] == ('A0', 'A1', 'A2', nm.exit_entry[0])

    def test_recursive_process_contents(self):
        """
        If set_contents has been called on contents that were extracted
        from an existing NumberedMenu, entry labels should remain the same.
        This ensures that process_contents doesn't actually add numbers
        to the labels, but only does it when get_displayed_contents()
        is called.
        """
        contents_1 = build_contents()
        nm = NumberedMenu(contents_1, get_mock_input(), get_mock_output(), name=nm_name, config={})
        # There will be an "exit" entry added in the end of new contents,
        # so we have to compensate for that
        labels_1 = [entry[0] for entry in contents_1]
        labels_2 = [entry[0] for entry in nm.contents]
        for i, label_1 in enumerate(labels_1):
            label_2 = labels_2[i]
            assert label_1 == label_2


if __name__ == '__main__':
    unittest.main()
