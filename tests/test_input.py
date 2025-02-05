"""tests output and input drivers and config parsing"""
import os
import unittest
from threading import Event
from mock import patch, Mock

try:
    from input.input import InputProcessor
    from helpers import cb_needs_key_state, KEY_PRESSED, KEY_RELEASED, KEY_HELD
except (ValueError, ImportError) as e:
    print("Absolute imports failed, trying relative imports")
    os.sys.path.append(os.path.dirname(os.path.abspath('.')))
    from input.input import InputProcessor
    from helpers import cb_needs_key_state, KEY_PRESSED, KEY_RELEASED, KEY_HELD

def get_mock_callback(**kwargs):
    m = Mock()
    m.configure_mock(**kwargs)
    m.configure_mock(__name__="test_callback")
    return m


class TestInputProcessor(unittest.TestCase):
    """Tests various InputProcessor features"""

    def test_key_state_processing_nokey_nostate(self):
        """Handling a callback - not passing key, not passing states"""
        i = InputProcessor({}, None)
        cb = get_mock_callback()
        dk = "KEY_DUMMY"
        i.handle_callback(cb, dk, None)
        assert(cb.call_args[0] == ())
        assert(cb.call_count == 1)
        i.handle_callback(cb, dk, KEY_PRESSED)
        assert(cb.call_args[0] == ())
        assert(cb.call_count == 2)
        i.handle_callback(cb, dk, KEY_RELEASED)
        assert(cb.call_count == 2)
        i.handle_callback(cb, dk, KEY_HELD)
        assert(cb.call_count == 2)

    def test_key_state_processing_key_nostate(self):
        """Handling a callback - not passing key, not passing states"""
        i = InputProcessor({}, None)
        cb = get_mock_callback()
        dk = "KEY_DUMMY"
        # Passing key, not processing states
        i.handle_callback(cb, dk, None, pass_key=True)
        assert(cb.call_args[0] == (dk,))
        assert(cb.call_count == 1)
        i.handle_callback(cb, dk, KEY_PRESSED, pass_key=True)
        assert(cb.call_args[0] == (dk,))
        assert(cb.call_count == 2)
        i.handle_callback(cb, dk, KEY_RELEASED, pass_key=True)
        assert(cb.call_count == 2)
        i.handle_callback(cb, dk, KEY_HELD, pass_key=True)
        assert(cb.call_count == 2)

    def test_key_state_processing_nokey_state(self):
        """Handling a callback - not passing key, passing states"""
        i = InputProcessor({}, None)
        cb = cb_needs_key_state(get_mock_callback())
        dk = "KEY_DUMMY"
        # Passing key, not processing states
        i.handle_callback(cb, dk, None)
        assert(cb.call_args[0] == (None,))
        assert(cb.call_count == 1)
        i.handle_callback(cb, dk, KEY_PRESSED)
        assert(cb.call_args[0] == (KEY_PRESSED,))
        assert(cb.call_count == 2)
        i.handle_callback(cb, dk, KEY_RELEASED)
        assert(cb.call_args[0] == (KEY_RELEASED,))
        assert(cb.call_count == 3)
        i.handle_callback(cb, dk, KEY_HELD)
        assert(cb.call_args[0] == (KEY_HELD,))
        assert(cb.call_count == 4)

    def test_key_state_processing_key_state(self):
        """Handling a callback - passing key, passing states"""
        i = InputProcessor({}, None)
        cb = cb_needs_key_state(get_mock_callback())
        dk = "KEY_DUMMY"
        # Passing key, not processing states
        i.handle_callback(cb, dk, None, pass_key=True)
        assert(cb.call_args[0] == (dk, None))
        assert(cb.call_count == 1)
        i.handle_callback(cb, dk, KEY_PRESSED, pass_key=True)
        assert(cb.call_args[0] == (dk, KEY_PRESSED))
        assert(cb.call_count == 2)
        i.handle_callback(cb, dk, KEY_RELEASED, pass_key=True)
        assert(cb.call_args[0] == (dk, KEY_RELEASED))
        assert(cb.call_count == 3)
        i.handle_callback(cb, dk, KEY_HELD, pass_key=True)
        assert(cb.call_args[0] == (dk, KEY_HELD))
        assert(cb.call_count == 4)


if __name__ == '__main__':
    unittest.main()
