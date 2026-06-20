menu_name = "I2C tools"

from zpui_lib.ui import Menu, Printer, PrettyPrinter, DialogBox, LoadingIndicator, UniversalInput, Refresher, IntegerAdjustInput, fvitg, Listbox
from zpui_lib.helpers import setup_logger, read_or_create_config, local_path_gen, write_config, get_platform

from collections import OrderedDict
from subprocess import check_output
from time import sleep, time
from copy import copy

import smbus

local_path = local_path_gen(__name__)
logger = setup_logger(__name__, "warning")
default_config = '{"recent_devices":[], "scan_range":"conservative", "default_bus":1, "timeout":3}'
config_path = local_path("config.json")
config = read_or_create_config(config_path, default_config, menu_name+" app")

def save_config(config):
    write_config(config, config_path)

current_bus = None
i = None
o = None

scan_ranges = {"conservative":(0x03, 0x77),
                       "full":(0x00, 0x7f)}

def get_current_bus_num():
    # TODO: grab I2C bus number from ZPUI config if it has an I2C port argument
    global current_bus
    if current_bus == None: # not yet set
        # 1 indicates /dev/i2c-1, for instance
        current_bus = config.get("default_bus", 1)
    return current_bus

def get_current_bus():
    return smbus.SMBus(get_current_bus_num())

def scan_i2c_bus():
    Printer("Scanning:", i, o, 0)
    try:
        bus = get_current_bus()
    except PermissionError as e:
         if e.errno == 13: # permission denied
             logger.exception("Error {}, permission denied, stopping scan! {}".format(e.errno, repr(e)))
             return "permission denied"
         else:
             raise e
    found_devices = OrderedDict()
    scan_range = config.get("scan_range", "conservative")
    if scan_range not in scan_ranges.keys(): #unknown scan range - config edited manually?
      scan_range = "conservative"
    scan_range_args = scan_ranges[scan_range]
    timeout = config.get("timeout", 3)
    start_time = time()
    for device in range(*scan_range_args):
      try: #If you try to read and it answers, it's there
         current_bus.read_byte(device)
      except PermissionError as e:
         if e.errno == 13: # permission denied
             logger.exception("Error {}, permission denied, stopping scan! {}".format(e.errno, repr(e)))
             return "permission denied"
         else:
             found_devices[device] = "permerr_{}".format(e.errno)
             logger.error("Errno {} unknown - can be used? {}".format(e.errno, repr(e)))
      except IOError as e:
         if e.errno == 16:
             found_devices[device] = "busy"
         elif e.errno in (5, 121):
             pass
         elif e.errno == 110:
             # bus crashout, scan isn't worth continuing
             logger.exception("Error {}, bus crashout, stopping scan! {}".format(e.errno, repr(e)))
             return "bus stuck"
             break
         else:
             found_devices[device] = "ioerr_{}".format(e.errno)
             logger.error("Errno {} unknown - can be used? {}".format(e.errno, repr(e)))
      else:
        found_devices[device] = "ok"
      if time() > start_time+timeout:
          found_devices["status"] = "timeout" # in-band signaling lolsob
          return found_devices
    return found_devices

device_notes = { # order defines first bus picked
    # "default" bus can vary depending on which CPU board is used!
    "snowdive":{"default":{
        0x1f: "RP2040",
        0x20: "addon?",
        0x21: "addon?",
        0x22: "FUSB302",
        0x24: "I2C expander A",
        0x25: "I2C expander B",
        0x2e: "TPM?",
        0x48: "touchscreen?",
        0x51: "RTC",
        0x56: "top PCB EEPROM",
    }},
    "blepis":{"default":{
        0x1f: "RP2040",
        0x20: "addon?",
        0x22: "FUSB302",
        0x2e: "TPM?",
        0x48: "touchscreen?",
        0x51: "RTC?",
    }},
    # beepy has same as blepis because some blepii still use "beepy" as device name. this will change!
    "beepy":{"default":{0x1f:"RP2040", 0x20: "addon?", 0x22:"FUSB302", 0x2e:"TPM?", 0x48:"touchscreen?", 0x51:"RTC?"}},
    "zpui_bc_v1_qwiic":{"default":{0x3c:"OLED", 0x3f:"keypad"}},
    "zpui_bc_v1":{"default":{0x3c:"OLED", 0x3f:"keypad"}},
    "zerophone_og":{1:{0x12:"ATMega328P", 0x20:"MCP23017"}},
}

context = None

def set_context(c):
    global context
    context = c
    context.set_provider("i2c_devices_get", scan_i2c_device_api)

def get_notes(zconfig=None, platform=None):
    if zconfig == None:
        from __main__ import zpui # hack for now
        zconfig = zpui.loaded_config()
    conf_default_bus = config.get("default_bus", 1) # app config default bus
    default_bus = zconfig.get("i2c", conf_default_bus) # global ZPUI config default bus
    if platform == None:
        platform = get_platform()
    notes = {}
    for device_name in device_notes.keys():
        if device_name in platform:
            notes_entry = device_notes.get(device_name, {})
            if "default" in notes_entry.keys(): # default bus special case
                default_entry = notes_entry.pop("default")
                fixed_entry = notes_entry.get(default_bus, {}) # might have a fixed-bus entry too, in the future
                fixed_entry.update(default_entry)
                notes_entry[default_bus] = fixed_entry
            notes.update(notes_entry)
            return notes

def scan_i2c_device_api():
    devices = scan_i2c_bus()
    if isinstance(devices, str):
        return devices
    if not devices: return {}
    all_notes = get_notes()
    current_bus_num = get_current_bus_num()
    notes = all_notes.get(current_bus_num, {})
    for dev, state in copy(devices).items():
        if dev in notes:
            description = notes[dev]
            devices[dev] = f"{state}-{description}"
    return devices

def scan_i2c_devices():
    try:
        with LoadingIndicator(i, o, message="Scanning I2C bus"):
            devices = scan_i2c_bus()
    except:
        logger.exception("I2C scan failed!")
        PrettyPrinter("I2C scan failed!", i, o, 3)
        return
    if isinstance(devices, str):
        PrettyPrinter("I2C scan failed! ({})".format(devices.capitalize()), i, o, 3)
        return
    if not devices:
        Printer("No devices found", i, o, 2)
    else:
        # user-friendly disambiguations for scan results
        all_notes = get_notes()
        current_bus_num = get_current_bus_num()
        notes = all_notes.get(current_bus_num, {})
        def ch():
            device_menu_contents = []
            has_timeouted = devices.pop("status", False) == "timeout"
            for dev, state in devices.items():
                if dev in notes:
                    description = notes[dev]
                    device_menu_contents.append(["{} ({}) - {}".format(hex(dev), description, state), lambda x=dev: i2c_device_menu(x)])
                else:
                    device_menu_contents.append(["{} - {}".format(hex(dev), state), lambda x=dev: i2c_device_menu(x)])
            if has_timeouted:
                device_menu_contents.append(["Timeouted!"])
            return device_menu_contents
        Menu([], i, o, contents_hook=ch, name="I2C tools app, scan results menu").activate()

def i2c_device_menu(addr):
    m_c = [["Simple read", lambda: i2c_read_ui(addr)],
           #["Simple write", lambda: i2c_write_ui(addr)],
           ["Register read", lambda: i2c_read_ui(addr, reg=True)]]
           #["Register write", lambda: i2c_write_ui(addr, reg=True)]]
    Menu(m_c, i, o, "I2C tools app, device menu for address {}".format(hex(addr))).activate()

last_values = []

def i2c_read_ui(address, reg=None):
    global last_values

    if reg == True:
        reg = UniversalInput(i, o, message="Register:", charmap="hex").activate()
        if reg is None: # User picked "cancel"
            return
    if isinstance(reg, basestring):
        reg = int(reg, 16)

    last_values = []

    def read_value(): # A helper function to read a value and format it into a list
        global last_values
        try:
            if reg:
                answer = "{} {}".format( hex(reg), hex(current_bus.read_byte_data(address, reg)) )
            else:
                answer = hex(current_bus.read_byte(address))
        except IOError:
            answer = "{} err".format(reg) if reg else "err"
        last_values.append(answer)
        return fvitg(list(reversed(last_values)), o)

    r = Refresher(read_value, i, o, refresh_interval=0.5)
    def change_interval(): # A helper function to adjust the Refresher's refresh interval while it's running
        new_interval = IntegerAdjustInput(int(r.refresh_interval), i, o, message="Refresh interval:").activate()
        if new_interval is not None:
            r.set_refresh_interval(new_interval)
    r.update_keymap({"KEY_RIGHT":change_interval})
    r.activate()


def change_range():
    global config
    dialogbox_options = [["Safe", "conservative"], ["Full", "full"], "c"]
    dialogbox = DialogBox(dialogbox_options, i, o, message="Scan range", name="I2C tools app range setting dialogbox")
    if config.get("scan_range", "conservative") == "full":
        # setting dialogbox position to the "full" option as it's currently selected
        dialogbox.set_start_option(1)
    new_range = dialogbox.activate()
    if new_range is not None:
        config["scan_range"] = new_range
        save_config(config)

def change_settings():
    settings = [["Scan range", change_range]]
    Menu(settings, i, o, "I2C tools app settings menu").activate()

def get_buses():
    try:
        c = check_output(["i2cdetect", "-l"])
    except:
        logger.exception("failure getting bus list =(")
        return {}
    if isinstance(c, bytes):
        c = c.decode("utf-8")
    lines = list(filter(None, c.split('\n')))
    buses = {}
    for line in lines:
        elements = line.strip().split("\t") # hopefully format won't change lmfao
        print(elements)
        i2c_marker = "i2c-"
        if elements[0].startswith(i2c_marker): # all is good
            num = int(elements[0][len(i2c_marker):])
            description = elements[2]
            buses[num] = description.strip()
    return buses

def set_bus():
    global current_bus
    buses = list(get_buses().items())
    buses.sort(key=lambda x: x[0])
    print(buses)
    choices = [[f"{num}: {name}", num] for num, name in buses]
    current_bus = get_current_bus_num()
    choice = Listbox(choices, i, o, name="I2C app bus choice listbox", selected=current_bus).activate()
    if choice != None:
        print(choice)
        config["default_bus"] = choice
        current_bus = choice
        save_config(config)

def callback():
    def ch():
        contents = [
            ["Scan bus (bus {})".format(get_current_bus_num()), scan_i2c_devices],
            ["Set bus", set_bus],
            ["Settings", change_settings],
        ]
        return contents
    Menu([], i, o, contents_hook=ch, name="I2C tools menu").activate()


# a tiny amount of unit tests
import unittest
class Tests(unittest.TestCase):
    def test_get_notes(self):
        """get_notes algo test"""
        snowdive_notes = device_notes["snowdive"]["default"]
        assert(get_notes(platform=["beepy", "snowdive"], zconfig={})[1] == snowdive_notes)
        beepy_notes = device_notes["beepy"]["default"]
        assert(get_notes(platform=["beepy"], zconfig={})[1] == beepy_notes)

if __name__ == "__main__":
    print(get_buses())
    unittest.main()
