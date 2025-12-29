menu_name = "I2C tools"

from subprocess import call
from zpui_lib.ui import Menu, Printer, PrettyPrinter, DialogBox, LoadingIndicator, UniversalInput, Refresher, IntegerAdjustInput, fvitg
from zpui_lib.helpers import setup_logger, read_or_create_config, local_path_gen, write_config, get_platform

from collections import OrderedDict
from time import sleep

import smbus

local_path = local_path_gen(__name__)
logger = setup_logger(__name__, "warning")
default_config = '{"recent_devices":[], "scan_range":"conservative"}'
config_path = local_path("config.json")
config = read_or_create_config(config_path, default_config, menu_name+" app")

def save_config(config):
    write_config(config, config_path)

current_bus = None

scan_ranges = {"conservative":(0x03, 0x77),
                       "full":(0x00, 0x7f)}

def scan_i2c_bus():
    global current_bus
    Printer("Scanning:", i, o, 0)
    try:
        current_bus = smbus.SMBus(1) # 1 indicates /dev/i2c-1
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
    return found_devices

device_notes = {
    "beepy":{0x1f:"RP2040", 0x22:"FUSB302", 0x2e:"TPM?", 0x48:"touchscreen?", 0x51:"RTC?"}, # need to separate it from Beepy
    "zpui_bc_v1_qwiic":{0x3c:"OLED", 0x3f:"keypad"},
    "zpui_bc_v1":{0x3c:"OLED", 0x3f:"keypad"},
    "zerophone_og":{0x12:"ATMega328P"},
}

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
        notes = {}
        for device in get_platform():
            notes_entry = device_notes.get(device, {})
            notes.update(notes_entry)
        def ch():
            device_menu_contents = []
            for dev, state in devices.items():
                if dev in notes:
                    description = notes[dev]
                    device_menu_contents.append(["{} ({}) - {}".format(hex(dev), description, state), lambda x=dev: i2c_device_menu(x)])
                else:
                    device_menu_contents.append(["{} - {}".format(hex(dev), state), lambda x=dev: i2c_device_menu(x)])
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

# Some globals for ZPUI
main_menu = None
callback = None
# Some globals for us
i = None
o = None

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

main_menu_contents = [
["Scan bus (bus 1)", scan_i2c_devices],
["Settings", change_settings]
]

def callback():
    main_menu = Menu(main_menu_contents, i, o, "I2C tools menu")
    main_menu.activate()

