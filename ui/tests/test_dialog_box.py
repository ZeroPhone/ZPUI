"""test for DialogBox"""
import os
import unittest

from mock import patch, Mock

try:
    from ui import DialogBox
    from ui.dialog import Canvas
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
        from dialog import DialogBox, Canvas
        fonts_dir = "../fonts"

def get_mock_input():
    return Mock()

def get_mock_output(rows=8, cols=21):
    m = Mock()
    m.configure_mock(rows=rows, cols=cols, type=["char"])
    return m

def get_mock_graphical_output(width=128, height=64, mode="1", cw=6, ch=8):
    m = get_mock_output(cols=width//cw, rows=height//ch)
    m.configure_mock(width=width, height=height, device_mode=mode, char_height=ch, char_width=cw, type=["b&w"])
    return m

db_name = "Test DialogBox"


class TestDialogBox(unittest.TestCase):
    """tests dialog box class"""

    def test_constructor(self):
        """tests constructor"""
        db = DialogBox([["Option", "option"]], get_mock_input(), get_mock_output(), name=db_name)
        self.assertIsNotNone(db)

    def test_init_options(self):
        """tests different ways of passing "values" - as string, as list of lists and as a list of both characters and lists."""
        i = get_mock_input()
        o = get_mock_output()
        d1 = DialogBox("ync", i, o, name=db_name + "1")
        assert (d1.values == [["Yes", True], ["No", False], ["Cancel", None]])
        d2 = DialogBox(["y", ["Hell no", False]], i, o, name=db_name + "2")
        assert (d2.values == [["Yes", True], ["Hell no", False]])
        d3 = DialogBox([["Hell yeah", True], ["Sod off", None]], i, o, name=db_name + "3")
        assert (d3.values == [["Hell yeah", True], ["Sod off", None]])

    def test_values_leakage(self):
        """tests whether the exit label of one DialogBox leaks into another"""
        i = get_mock_input()
        o = get_mock_output()
        d1 = DialogBox("ync", i, o, name=db_name + "1")
        d2 = DialogBox(["y", ["Hell no", False]], i, o, name=db_name + "2")
        d3 = DialogBox([["Hell yeah", True], ["Sod off", None]], i, o, name=db_name + "3")
        assert (d1.values != d2.values)
        assert (d2.values != d3.values)
        assert (d1.values != d3.values)

    def test_left_key_returns_none(self):
        db = DialogBox("ync", get_mock_input(), get_mock_output(), name=db_name)
        db.refresh = lambda *args, **kwargs: None

        # Checking at the start of the options
        def scenario():
            db.move_left()
            assert not db.in_foreground

        with patch.object(db, 'idle_loop', side_effect=scenario) as p:
            return_value = db.activate()
        assert return_value is None

        # Going to the right and then going to the left again
        def scenario():
            db.move_right()
            db.move_left() #At this point, shouldn't exit
            assert db.in_foreground
            db.move_left()
            assert not db.in_foreground

        with patch.object(db, 'idle_loop', side_effect=scenario) as p:
            return_value = db.activate()
        assert return_value is None

    def test_graphical_display_redraw(self):
        o = get_mock_graphical_output()
        db = DialogBox("ync", get_mock_input(), o, name=db_name)
        Canvas.fonts_dir = fonts_dir
        # Exiting immediately, but we should get at least one redraw
        def scenario():
            db.deactivate()  # KEY_LEFT
            assert not db.in_foreground

        with patch.object(db, 'idle_loop', side_effect=scenario) as p:
            return_value = db.activate()
        assert o.display_image.called
        assert o.display_image.call_count == 1 #One in to_foreground

    def test_start_option(self):
        db = DialogBox("ync", get_mock_input(), get_mock_output(), name=db_name)
        db.refresh = lambda *args, **kwargs: None
        db.set_start_option(1) #So, "No" option would be selected

        def scenario():
            db.accept_value()  # KEY_ENTER
            assert not db.in_foreground  # Should exit

        with patch.object(db, 'idle_loop', side_effect=scenario) as p:
            return_value = db.activate()
        assert return_value is False #Second element - No, means False

    def test_returns_right_values(self):
        """Checking that going to different options returns the right values"""
        # Checking first option - Yes
        db = DialogBox("ync", get_mock_input(), get_mock_output(), name=db_name)
        def scenario():
            db.accept_value()  # KEY_ENTER
            assert not db.in_foreground  # Should exit

        with patch.object(db, 'idle_loop', side_effect=scenario) as p:
            return_value = db.activate()
        assert return_value is True #First element - Yes, means True

        # Checking second option - No
        db = DialogBox("ync", get_mock_input(), get_mock_output(), name=db_name)
        def scenario():
            db.move_right()
            db.accept_value()  # KEY_ENTER
            assert not db.in_foreground  # Should exit

        with patch.object(db, 'idle_loop', side_effect=scenario) as p:
            return_value = db.activate()
        assert return_value is False #Second element - No, means False

        # Checking second option - Cancel
        db = DialogBox("ync", get_mock_input(), get_mock_output(), name=db_name)
        def scenario():
            db.move_right()
            db.move_right()
            db.accept_value()  # KEY_ENTER
            assert not db.in_foreground  # Should exit

        with patch.object(db, 'idle_loop', side_effect=scenario) as p:
            return_value = db.activate()
        assert return_value is None #Last element - Cancel, means None

    def test_shows_data_on_screen(self):
        """Tests whether the DialogBox outputs data on screen when it's ran"""
        i = get_mock_input()
        o = get_mock_output()
        db = DialogBox("ync", i, o, name=db_name)

        def scenario():
            db.deactivate()

        with patch.object(db, 'idle_loop', side_effect=scenario) as p:
            db.activate()
            #The scenario should only be called once
            assert db.idle_loop.called
            assert db.idle_loop.call_count == 1

        assert o.display_data.called
        assert o.display_data.call_count == 1 #One in to_foreground
        assert o.display_data.call_args[0] == ('Are you sure?', '    Yes No Cancel')

if __name__ == '__main__':
    unittest.main()
