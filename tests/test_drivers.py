"""tests output and input drivers and config parsing"""
import os
import json
import unittest
import traceback
from copy import deepcopy
from threading import Event
from mock import patch, Mock

try:
    import main as main_py
    from input.drivers import test_input, pi_gpio, pi_gpio_matrix
    config_path = "tests/test_config.json"
except (ValueError, ImportError) as e:
    print("Absolute imports failed, trying relative imports")
    os.sys.path.append(os.path.dirname(os.path.abspath('.')))
    import main as main_py
    from input.drivers import test_input, pi_gpio, pi_gpio_matrix
    config_path = "test_config.json"


with open(config_path, 'r') as f:
    base_config = json.load(f)


class TestDrivers(unittest.TestCase):
    """Tests various drivers. Mostly tests various config permutations, as well as
    base drivers like ``luma_driver.py``, `input.init()` and `output.init()`."""

    def test_sh1106(self):
        output_config = {"driver":"sh1106", "kwargs":{"hw":"dummy"}}
        config = deepcopy(base_config)
        config["output"][0] = output_config
        assert(config["input"][0]["driver"] == "test_input")
        with patch.object(main_py, 'load_config') as mocked:
            mocked.return_value = (config, "test_config.json")
            i, o = main_py.init()
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))

    def test_ssd1306(self):
        output_config = {"driver":"ssd1306", "kwargs":{"hw":"dummy"}}
        config = deepcopy(base_config)
        config["output"][0] = output_config
        assert(config["input"][0]["driver"] == "test_input")
        with patch.object(main_py, 'load_config') as mocked:
            mocked.return_value = (config, "test_config.json")
            i, o = main_py.init()
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))

    def test_st7735(self):
        output_config = {"driver":"st7735", "kwargs":{"hw":"dummy"}}
        config = deepcopy(base_config)
        config["output"][0] = output_config
        assert(config["input"][0]["driver"] == "test_input")
        with patch.object(main_py, 'load_config') as mocked:
            mocked.return_value = (config, "test_config.json")
            i, o = main_py.init()
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))

    def test_st7735_with_params(self):
        output_config = {"driver":"st7735", "kwargs":{"hw":"dummy", "rotate":1, \
                         "h_offset":1, "v_offset":2, "height":160}}
        config = deepcopy(base_config)
        config["output"][0] = output_config
        assert(config["input"][0]["driver"] == "test_input")
        with patch.object(main_py, 'load_config') as mocked:
            mocked.return_value = (config, "test_config.json")
            i, o = main_py.init()
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))
        assert(o.height == 160)

    def test_sh1106_with_backlight(self):
        output_config = {"driver":"sh1106", "kwargs":{"hw":"dummy", "backlight_interval":10}}
        config = deepcopy(base_config)
        config["output"][0] = output_config
        assert(config["input"][0]["driver"] == "test_input")
        with patch.object(main_py, 'load_config') as mocked:
            mocked.return_value = (config, "test_config.json")
            i, o = main_py.init()
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))

    @unittest.skip("broken test, can't properly patch the imports =(")
    def test_pygame_driver(self):
        input_config = {"driver":"pygame_input"}
        config = deepcopy(base_config)
        config["input"][0] = input_config
        assert(config["output"][0]["driver"] == "test_output")
        module_patch = patch.dict('sys.modules', {"luma.emulator.device":Mock(), \
                                                  "luma.emulator":Mock()})
        module_patch.start()
        import sys; print([(key, sys.modules[key]) for key in sys.modules.keys() if key.startswith('luma.emulator')])
        sys.modules['luma.emulator'].configure_mock(device2=Mock())
        print(sys.modules['luma.emulator'])
        print(sys.modules['luma.emulator.device'])
        import emulator as emulator_py
        with patch.object(emulator_py.Emulator, 'init_hw') as init_hw, \
          patch.object(emulator_py.Emulator, 'runner') as runner, \
          patch.object(emulator_py.EmulatorProxy, 'start_process'):
            with patch.object(main_py, 'load_config') as mocked:
                mocked.return_value = (config, "test_config.json")
                i, o = main_py.init()
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))
        module_patch.stop()
        print([(key, sys.modules[key]) for key in sys.modules.keys() if key.startswith('luma.emulator')])
        # so that no ugly exception is raised when the test finishes
        main_py.input_processor.atexit()

    def test_hid_driver(self):
        input_config = {"driver":"hid", "kwargs":{"name":"test"}}
        config = deepcopy(base_config)
        config["input"][0] = input_config
        assert(config["output"][0]["driver"] == "test_output")
        module_patch = patch.dict('sys.modules', {"evdev":Mock()})
        module_patch.start()
        import sys; #print([(key, sys.modules[key]) for key in sys.modules.keys() if key.startswith('evdev')])
        sys.modules['evdev'].configure_mock(device2=Mock())
        #print(sys.modules['evdev'])
        from input.drivers import hid
        with patch.object(hid.InputDevice, 'init_hw') as init_hw, \
          patch.object(hid.InputDevice, 'runner') as runner:
            with patch.object(main_py, 'load_config') as mocked:
                mocked.return_value = (config, "test_config.json")
                i, o = main_py.init()
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))
        module_patch.stop()
        # Checking if we removed all imports
        # print([(key, sys.modules[key]) for key in sys.modules.keys() if key.startswith('evdev')])
        # so that no ugly exception is raised when the test finishes
        main_py.input_processor.atexit()

    @unittest.skip("broken test, can't properly patch the imports =(")
    def test_pi_gpio_driver(self):
        input_config = {"driver":"pi_gpio"}
        config = deepcopy(base_config)
        config["input"][0] = input_config
        assert(config["output"][0]["driver"] == "test_output")
        with patch.object(pi_gpio.InputDevice, 'init_hw') as init_hw, \
          patch.object(pi_gpio.InputDevice, 'runner') as runner:
            with patch.object(main_py, 'load_config') as mocked:
                mocked.return_value = (config, "test_config.json")
                i, o = main_py.init()
            assert(init_hw.called_once())
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))
        # so that no ugly exception is raised when the test finishes
        main_py.input_processor.atexit()

    @unittest.skip("broken test, can't properly patch the imports =(")
    def test_pi_gpio_matrix_driver(self):
        input_config = {"driver":"pi_gpio_matrix"}
        config = deepcopy(base_config)
        config["input"][0] = input_config
        assert(config["output"][0]["driver"] == "test_output")
        with patch.object(pi_gpio_matrix.InputDevice, 'init_hw') as init_hw, \
          patch.object(pi_gpio_matrix.InputDevice, 'runner') as runner:
            with patch.object(main_py, 'load_config') as mocked:
                mocked.return_value = (config, "test_config.json")
                i, o = main_py.init()
            assert(init_hw.called_once())
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))
        # so that no ugly exception is raised when the test finishes
        main_py.input_processor.atexit()

    def test_custom_i2c_driver(self):
        input_config = {"driver":"custom_i2c"}
        config = deepcopy(base_config)
        config["input"][0] = input_config
        assert(config["output"][0]["driver"] == "test_output")
        module_patch = patch.dict('sys.modules', {"smbus":Mock()})
        module_patch.start()
        from input.drivers import custom_i2c
        with patch.object(custom_i2c.InputDevice, 'init_hw') as init_hw, \
          patch.object(custom_i2c.InputDevice, 'runner') as runner:
            with patch.object(main_py, 'load_config') as mocked:
                mocked.return_value = (config, "test_config.json")
                i, o = main_py.init()
            assert(init_hw.called_once())
        assert(isinstance(i, main_py.input.InputProxy))
        assert(isinstance(o, main_py.output.OutputProxy))
        # so that no ugly exception is raised when the test finishes
        main_py.input_processor.atexit()
        module_patch.stop()

    def test_input_driver_attach_detach(self):
        config = deepcopy(base_config)
        assert(config["output"][0]["driver"] == "test_output")
        assert(config["input"][0]["driver"] == "test_input")
        with patch.object(main_py, 'load_config') as mocked:
            mocked.return_value = (config, "test_config.json")
            i, o = main_py.init()
        assert(len(main_py.input_processor.drivers) == 1)
        name = main_py.input_processor.attach_driver(test_input.InputDevice())
        assert(len(main_py.input_processor.drivers) == 2)
        main_py.input_processor.detach_driver(name)
        assert(len(main_py.input_processor.drivers) == 1)
        # so that no ugly exception is raised when the test finishes
        main_py.input_processor.atexit()

if __name__ == '__main__':
    unittest.main()
