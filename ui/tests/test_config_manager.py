"""test for Checkbox"""
import os
import unittest

from mock import patch, Mock

try:
    from ui.config_manager import UIConfigManager
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
        elif name == 'ui.utils':
            import utils
            return utils
        return orig_import(name, *args, **kwargs)

    with patch('__builtin__.__import__', side_effect=import_mock):
        from config_manager import UIConfigManager


class TestUIConfigManager(unittest.TestCase):
    """tests config manager class"""

    def test_update_config(self):
        cm = UIConfigManager()
        config_a = {
            "a": {"this1": "is original"},
            "b": {"value": "to_be_replaced"},
            "c": "old_element_value",
            "e": {"this": "remains"}
        }
        config_b = {
            "a": {"this2": "is_new"},
            "b": {"value": "was_replaced"},
            "c": "new_element_value",
            "d": {"this": "is_new"}
        }
        new_config = cm.update_config(config_a, config_b)
        self.assertEqual(new_config, {
            'a': {'this1': 'is original', 'this2': 'is_new'},
            'b': {'value': 'was_replaced'},
            'c': 'new_element_value',
            'd': {'this': 'is_new'},
            'e': {'this': 'remains'}
        })


if __name__ == '__main__':
    unittest.main()
