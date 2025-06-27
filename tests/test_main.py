"""tests for the main.py launcher"""
import os
import unittest
import traceback

from threading import Event
from mock import patch, Mock

try:
    from .. import main as main_py
except (ValueError, ImportError) as e:
    print("Absolute imports failed, trying relative imports")
    os.chdir('..')
    os.sys.path.append(os.path.abspath('.'))
    # Store original __import__
    orig_import = __import__

    def import_mock(name, *args, **kwargs):
        if name in ['helpers'] and not kwargs:
            #Have to filter for kwargs since there's a package in 'json'
            #that calls __builtins__.__import__ with keyword arguments
            #and we don't want to mock that call
            return Mock()
        return orig_import(name, *args, **kwargs)

    #with patch('__builtin__.__import__', side_effect=import_mock):
    import main as main_py

class TestMainPy(unittest.TestCase):
    """tests main.py launcher"""
    test_config_paths = ["tests/test_config.json", "test_config.json"]

    @patch.object(main_py, 'config_paths', test_config_paths)
    def test_load_config(self):
        """Tests whether main.py=>load_config loads test config files"""
        config, config_path = main_py.load_config()
        assert(config_path in self.test_config_paths)
        assert("input" in config)
        assert("output" in config)

    @patch.object(main_py, 'config_paths', test_config_paths)
    def test_init(self):
        i, o = main_py.init()
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))

    @patch.object(main_py, 'config_paths', test_config_paths)
    def test_launch_test_app(self):
        e_wrapper_called = Event()
        def e_wrapper(cb):
            e_wrapper_called.set()
        # exception_wrapper here is used as a way of detecting that the very last line of `launch()` gets executed
        with patch.object(main_py, 'exception_wrapper', side_effect = e_wrapper):
            main_py.launch(name="apps/example_apps/test/")
        assert(e_wrapper_called.is_set())

    @patch.object(main_py, 'config_paths', test_config_paths)
    def test_launch_test_all(self):
        e_wrapper_called = Event()
        def e_wrapper(cb):
            e_wrapper_called.set()
        # exception_wrapper here is used as a way of detecting that the very last line of `launch()` gets executed
        with patch.object(main_py, 'exception_wrapper', side_effect = e_wrapper):
            main_py.launch()
        assert(e_wrapper_called.is_set())


if __name__ == '__main__':
    unittest.main()

