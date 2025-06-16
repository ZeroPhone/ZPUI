menu_name = "Assistant status"

from serial import Serial

from zpui_lib.ui import Refresher

serial_device = "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0371-if00-port0"
port = Serial(serial_device, 115200, timeout=1)

def get_voltage():
    port.flushInput()
    answer = at_command('AT+CBC')
    if answer is None: return None
    if not answer.startswith('+CBC'): return None
    voltage_str = answer.split(':')[1].split(',')[2]
    voltage = int(voltage_str)/1000.0
    return voltage

def at_command(command):
    port.write(command+b'\n')
    echo = port.readline(len(command)+10)
    if not command in echo:
        return None
    answer = port.readline(1000)
    return answer.strip()

def show_status():
    bat_voltage = get_voltage()
    if bat_voltage is not None:
        bat_voltage = round(bat_voltage, 2)
    data = [
    "Battery: "+str(bat_voltage).rjust(o.cols-len("Battery: "))]
    return data

i = None; o = None

def callback():
    Refresher(show_status, i, o, 0.1, name="Assistant status monitor").activate()

def init_app(input, output):
    global i, o
    i = input; o = output

