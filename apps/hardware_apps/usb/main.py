from helpers import setup_logger

menu_name = "USB control"

from zerophone_hw import USB_DCDC
from ui import Menu, Printer
from actions import BackgroundAction
from time import sleep
import os

logger = setup_logger(__name__, "warning")
i = None
o = None
context = None

dcdc = USB_DCDC()
dcdc_state = False

def get_menu_name():
    return "USB on" if dcdc_state else "USB off"

def set_context(c):
    global context
    context = c
    call_usb_app = lambda: context.request_switch()
    context.register_action(BackgroundAction("usb_toggle", dcdc_toggle, menu_name=get_menu_name, description="Switches USB port power on or off", aux_cb=call_usb_app))

def dcdc_off_on():
    global dcdc_state
    dcdc.off()
    sleep(0.5)
    dcdc.on()
    dcdc_state = True

def dcdc_on():
    global dcdc_state
    dcdc.on()
    dcdc_state = True

def dcdc_off():
    global dcdc_state
    dcdc.off()
    dcdc_state = False

def dcdc_toggle():
    dcdc_off() if dcdc_state else dcdc_on()

usb_file = None
usb_file_base_dir = "/sys/devices/platform/soc/"
usb_control_file = "buspower"
usb_full_path = None

def usb_off_on():
    with open(usb_full_path, "w") as f:
        f.write("0")
        sleep(0.5)
        f.write("1")

def usb_on():
    with open(usb_full_path, "w") as f:
        f.write("1")

def usb_off():
    with open(usb_full_path, "w") as f:
        f.write("0")

main_menu_contents = [ 
["Restart 5V DC-DC", dcdc_off_on],
["Turn 5V DC-DC on", dcdc_on],
["Turn 5V DC-DC off", dcdc_off],
["Restart USB bus", usb_off_on],
["Turn USB bus on", usb_on],
["Turn USB bus off", usb_off]
]

def init_app(input, output):
    global i, o, usb_file, usb_full_path
    i = input; o = output
    #Find the usb device control directory
    device_files = os.listdir(usb_file_base_dir)
    usb_files = [file for file in device_files if file.endswith(".usb")]
    if not usb_files:
        logger.error("Can't find suitable USB file at {}! What's wrong with this hardware?".format(usb_file_base_dir))
        raise IOError
    usb_file = usb_files[0] #I'm guessing having more than one file would mean 
    #having more than one USB controller, so this is not Raspberry Pi stuff anymore
    #and I can only test this on a Pi right now.
    usb_full_path = os.path.join(usb_file_base_dir, usb_file, usb_control_file)
    if not os.path.exists(usb_full_path):
        logger.error("Can't find {} file at {}! What's wrong with this hardware?".format(usb_control_file, usb_full_path))
        raise IOError
        
def callback():
    Menu(main_menu_contents, i, o, "USB app menu").activate()

