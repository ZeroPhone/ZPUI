from zpui_lib.helpers import setup_logger
import unittest

logger = setup_logger(__name__, "info")

def update_driver(device_config, user_config, device):
    # looking for input/output driver entries that modify the base driver
    update = None
    drivers = user_config[device]
    if isinstance(drivers, str):
        # one driver and it's just a string - can't impact anything
        drivers = [drivers]
    elif isinstance(drivers, dict):
        # one driver
        drivers = [drivers]
    if isinstance(drivers, list):
        for driver in drivers:
            if isinstance(driver, dict) and driver["driver"] == 0: # special case value for modifying the OG driver
                # modification!
                for key in driver:
                    # is the driver ready for modification? if not, make it ready
                    if isinstance(device_config, str):
                        device_config = {"driver":device_config}
                    if key == "driver": continue
                    device_config[key] = driver[key]
            else:
                # simply append the user-specified driver to the base config
                if isinstance(device_config, (str, dict)):
                    device_config = [device_config]
                device_config.append(driver)
    logger.info("{} config expanded into {} using {}".format(repr(device), repr(device_config), repr(user_config)))
    return device_config

def set_status_bar_height(config, height):
    if "app_manager" not in config:
        config["app_manager"] = {}
    if "status_bar_height" not in config["app_manager"]:
        config["app_manager"]["status_bar_height"] = height
        logger.info("Set status bar height to {}".format(height))
    else:
        logger.info("Tried to set status bar height to {}, but it's already {}".format(height, config["app_manager"]["status_bar_height"]))

def update_config(config, input_config, output_config):
    # looking out for modifications to the proposed config
    if "input" in config:
        input_config = update_driver(input_config, config, "input")
    if "output" in config:
        output_config = update_driver(output_config, config, "output")
    return input_config, output_config

def get_io_configs(config):
    if "device" in config:
        logger.debug("getting config for device {}, starting from {}".format(config["device"], config))
        device = config["device"]
        if isinstance(device, str):
            device_name = device
        else:
            device_name = device["driver"]
        device_fun = devices[device_name]
        input_config, output_config = device_fun(config)
        input_config, output_config = update_config(config, input_config, output_config)
        logger.info("created configs, input: {}, output: {}".format(input_config, output_config))
        # TODO merge 'device' and 'input'/'output' configs!!
        return input_config, output_config
    else:
        if "input" not in config:
            raise ValueError("No 'device' or 'input' section found in config - an input device is required!")
        if "output" not in config:
            raise ValueError("No 'device' or 'output' section found in config - an output device is required!")
        return config["input"], config["output"]

def config_emulator(config):
    io = ["pygame_input", "pygame_emulator"]
    if "resolution" in config:
        res_str = config["resolution"]
        sep = "x" if "x" in res_str else None
        sep = "*" if "*" in res_str else sep
        if not sep:
            raise ValueError("The 'resolution' parameter needs to be in WIDxHEI or WID*HEI format! Got: {}".format(res_str))
        width, height = map(int, res_str.split(sep))
        io[1] = {"driver":io[1]}
        io[1]["width"] = width
        io[1]["height"] = height
    if "mode" in config:
        if not isinstance(io[1], dict):
            io[1] = {"driver":io[1]}
        io[1]["mode"] = str(config["mode"]) # str is fix for mode "1"
    if "resolution" in config:
        if height >= 240:
            set_status_bar_height(config, 30)
    return io

def config_zpog(config):
    io = ["custom_i2c", "sh1106"]
    if "i2c" in config:
        io[0] = {"driver":io[0]}
        io[0]["bus"] = int(config.get("i2c", 1))
        io[1] = {"driver":io[1]}
        io[1]["port"] = int(config.get("i2c", 1))
    return io

def rotate_zpui_bc(io, config):
    i, o = io
    rotate = config["device"]["rotate"].upper()[0]
    if rotate not in "NESW":
        logger.error("Faulty rotate received ({}), doing North rotation as default".format(repr(config["device"]["rotate"])))
        rotate = "N"
    # we rotate the buttons, for now
    mappings = {
        "N":n_mapping,
        "E":e_mapping,
        "S":s_mapping,
        "W":w_mapping,
    }
    if isinstance(i, str):
        i = {"driver":i}
    i["mapping"] = mappings[rotate]
    io = i, o
    return io

def config_zpui_bc_v1_qwiic(config):
    io = ({"driver":"pcf8574", "addr":0x3f}, {"driver":"sh1106", "hw":"i2c"})
    if "i2c" in config:
        io[0]["bus"] = int(config.get("i2c", 1))
        io[1]["port"] = int(config.get("i2c", 1))
    if isinstance(config["device"], dict):
        if "rotate" in config["device"]:
            io = rotate_zpui_bc(io, config)
    return io

def config_zpui_bc_v1(config):
    io = ({"driver":"pi_gpio", "button_pins":[27, 25, 24, 17, 23, 5, 22, 18]}, {"driver":"sh1106", "hw":"i2c"})
    if "i2c" in config:
        io[1]["port"] = int(config.get("i2c", 1))
    if isinstance(config["device"], dict):
        if "rotate" in config["device"]:
            io = rotate_zpui_bc(io, config)
    return io

def config_waveshare_oled_hat(config):
    io = ({"driver":"pi_gpio", "button_pins":[6, 21, 26, 20, 19, 5, 16, 13]}, {"driver":"sh1106", "hw":"spi", "dc":24, "rst":25})
    if "screen_hw" in config:
        if config["screen_hw"] == "i2c":
            io[1]["hw"] = "i2c"
            io[1].pop("dc")
    if "i2c" in config:
        io[1]["port"] = int(config.get("i2c", 1))
    if isinstance(config["device"], dict):
        if "rotate" in config["device"]:
            io = rotate_zpui_bc(io, config)
    return io

def config_beepy(config):
    io = [{"driver":"pcf8574", "addr":0x3f}, {"driver":"beepy_fb", "fb_num":1}] # by default, the pcf driver is used as a backup, same config as the ZPUI businesscard
    if "fb_num" in config:
        io[1]["fb_num"] = config.get("fb_num", 1)
    if "i2c" in config:
        io[0]["bus"] = int(config.get("i2c", 1))
    io[0] = [io[0]]
    io[0].append({"driver":"beepy_hid"})
    set_status_bar_height(config, 30)
    return io

n_mapping = [
        "KEY_UP",
        "KEY_PROG2",
        "KEY_RIGHT",
        "KEY_F3",
        "KEY_DOWN",
        "KEY_LEFT",
        "KEY_F4",
        "KEY_ENTER",
]
e_mapping = [
        "KEY_LEFT",
        "KEY_PROG2",
        "KEY_UP",
        "KEY_F3",
        "KEY_RIGHT",
        "KEY_DOWN",
        "KEY_F4",
        "KEY_ENTER",
]
s_mapping = [
        "KEY_DOWN",
        "KEY_PROG2",
        "KEY_LEFT",
        "KEY_F4",
        "KEY_UP",
        "KEY_RIGHT",
        "KEY_F3",
        "KEY_ENTER",
]
w_mapping = [
        "KEY_RIGHT",
        "KEY_PROG2",
        "KEY_DOWN",
        "KEY_F4",
        "KEY_LEFT",
        "KEY_UP",
        "KEY_F3",
        "KEY_ENTER",
]

devices = {
  "emulator":config_emulator,
  "zerophone_og":config_zpog,
  "zpui_bc_v1_qwiic":config_zpui_bc_v1_qwiic,
  "zpui_bc_v1":config_zpui_bc_v1,
  "waveshare_oled_hat":config_waveshare_oled_hat,
  "beepy":config_beepy,
}


#
#
#
# Breakage of any of these tests
# must be considered very carefully
#
#
#

class TestCombination(unittest.TestCase):

    def test_simple(self):
        """tests that it runs when a device isn't provided"""
        config = {"input":"test1", "output":"test2"}
        i, o = get_io_configs(config)
        assert(i == "test1")
        assert(o == "test2")

    def test_emulator(self):
        """tests that it runs when a device isn't provided"""
        config = {"device":"emulator"}
        i, o = get_io_configs(config)
        assert(i == "pygame_input")
        assert(o == "pygame_emulator")

    def test_zpog(self):
        """tests that zpog config parses"""
        config = {"device":"zerophone_og"}
        i, o = get_io_configs(config)
        assert(o == "sh1106")
        assert(i == "custom_i2c")

    def test_zpbc1q(self):
        """tests that it zp businesscard v1 qwiic config parses"""
        config = {"device":"zpui_bc_v1_qwiic"}
        i, o = get_io_configs(config)
        assert(i == {'driver': 'pcf8574', 'addr': 63})
        assert(o == {'driver': 'sh1106', 'hw': 'i2c'})

    def test_zpbc1q_rotate(self):
        """tests that it zp businesscard v1 qwiic config with rotation parses"""
        config = {"device":{"driver":"zpui_bc_v1_qwiic", "rotate":"N"}}
        i, o = get_io_configs(config)
        assert(i['driver'] == 'pcf8574')
        assert(i['addr'] == 63)
        assert(i['mapping'] == n_mapping)
        assert(o == {'driver': 'sh1106', 'hw': 'i2c'})

    def test_zpbc1_rotate(self):
        """tests that it zp businesscard v1 config with rotation parses"""
        config = {"device":{"driver":"zpui_bc_v1", "rotate":"N"}}
        i, o = get_io_configs(config)
        assert(i['driver'] == 'pi_gpio')
        assert(i['mapping'] == n_mapping)
        assert(o == {'driver': 'sh1106', 'hw': 'i2c'})

    def test_zpbc1(self):
        """tests that it zp businesscard v1 config parses"""
        config = {"device":"zpui_bc_v1"}
        i, o = get_io_configs(config)
        assert(i == {'driver': 'pi_gpio', 'button_pins': [27, 25, 24, 17, 23, 5, 22, 18]})
        assert(o == {'driver': 'sh1106', 'hw': 'i2c'})

    def test_mods_drivers(self):
        config = {"device":"emulator", "input":{"driver":0, "test1":"test2"}}
        i, o = get_io_configs(config)
        assert(i == {'driver': 'pygame_input', 'test1': 'test2'})
        assert(o == 'pygame_emulator')

    def test_mods_and_adds_drivers(self):
        config = {"device":"emulator", "input":[{"driver":0, "test1":"test2"}, "test3"], "output":[{"driver":0, "test4":"test5"}, "test6"]}
        i, o = get_io_configs(config)
        assert(i == [{'driver': 'pygame_input', 'test1': 'test2'}, 'test3'])
        assert(o == [{'driver': 'pygame_emulator', 'test4': 'test5'}, 'test6'])

    def test_zpbc1_i2cbus(self):
        """tests that it zp businesscard v1 config can be modded with i2c"""
        config = {"device":"zpui_bc_v1", "i2c":"2"}
        i, o = get_io_configs(config)
        assert(i == {'driver': 'pi_gpio', 'button_pins': [27, 25, 24, 17, 23, 5, 22, 18]})
        assert(o == {'driver': 'sh1106', 'hw': 'i2c', 'port': 2})

    def test_zpbc1q_i2cbus(self):
        """tests that it zp businesscard v1 qwiic config parses"""
        config = {"device":"zpui_bc_v1_qwiic", "i2c":"2"}
        i, o = get_io_configs(config)
        assert(i == {'driver': 'pcf8574', 'addr': 63, 'bus': 2})
        assert(o == {'driver': 'sh1106', 'hw': 'i2c', 'port': 2})

    def test_waveshare_oled(self):
        """tests that zp waveshare oled hat config works"""
        config = {"device":"waveshare_oled_hat"}
        i, o = get_io_configs(config)
        assert(i == {'driver': 'pi_gpio', 'button_pins': [6, 21, 26, 20, 19, 5, 16, 13]})
        assert(o == {'driver': 'sh1106', 'hw': 'spi', 'dc': 24, 'rst': 25})

    def test_waveshare_oled_i2c(self):
        """tests that waveshare oled hat config with screen hw parses"""
        config = {"device":"waveshare_oled_hat", "screen_hw":"i2c"}
        i, o = get_io_configs(config)
        assert(i == {'driver': 'pi_gpio', 'button_pins': [6, 21, 26, 20, 19, 5, 16, 13]})
        assert(o == {'driver': 'sh1106', 'hw': 'i2c', "rst": 25})

    def test_zpog_i2cbus(self):
        """tests that zpog config parses"""
        config = {"device":"zerophone_og", "i2c": "2"}
        i, o = get_io_configs(config)
        assert(o == {"driver": "sh1106", "port": 2})
        assert(i == {"driver":"custom_i2c", "bus": 2})

    def test_emulator_resolution(self):
        """tests that it runs with emulator driver and resolution provided"""
        config = {"device":"emulator", "resolution":"400x240"}
        i, o = get_io_configs(config)
        assert(i == "pygame_input")
        assert(o == {'driver': 'pygame_emulator', 'width': 400, 'height': 240})
        config = {"device":"emulator", "resolution":"400*240"}
        i, o = get_io_configs(config)
        assert(i == "pygame_input")
        assert(o == {'driver': 'pygame_emulator', 'width': 400, 'height': 240})

    def test_emulator_mode(self):
        """tests that it runs with emulator driver and resolution provided"""
        config = {"device":"emulator", "mode":"RGB"}
        i, o = get_io_configs(config)
        assert(i == "pygame_input")
        assert(o == {'driver': 'pygame_emulator', 'mode': "RGB"})
        config = {"device":"emulator", "resolution":"400*240", "mode":"RGB"}
        assert(i == "pygame_input")
        assert(o == {'driver': 'pygame_emulator', 'mode': "RGB"})
        # tests for a bug where mode "1" is YAML parsed as integer
        config = {"device":"emulator", "resolution":"400*240", "mode":1}
        i, o = get_io_configs(config)
        assert(i == "pygame_input")
        assert(o == {'driver': 'pygame_emulator', "mode":"1", 'width': 400, 'height': 240})

    def test_beepy(self):
        """tests that beepy config works"""
        config = {"device":"beepy"}
        i, o = get_io_configs(config)
        assert(i == [{'driver': 'pcf8574', 'addr': 63}, {'driver': 'beepy_hid'}])
        assert(o == {'driver': 'beepy_fb', 'fb_num': 1})


if __name__ == '__main__':
    unittest.main()
