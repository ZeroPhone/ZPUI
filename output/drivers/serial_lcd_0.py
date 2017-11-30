from serial import Serial

#ser_port = "/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A9CJVD59-if00-port0" #send that to settings or something something automagical
from output.output import OutputDevice

"""
 NOT WORKING
 The first output driver I did. The idea was having an Arduino which would have a 16x2 screen connected,
 take a string over serial, clear the screen, put first 16 characters on the first line, second 16 characters on the second line
 and discard the rest.
 Hey, it worked. I'm leaving this here in case you need an example or something.
 Can't enable backlight, can't just clear the screen, is config-compatible and theoretically is even working. No Arduino code included.
"""
class Screen(OutputDevice):
    """Class that has all the screen control functions and defines"""
    type = ["char"]

    def __init__(self, ser_port=None, ser_speed=115200, rows=2, cols=16):
        self.rows = rows
        self.cols = cols
        self.serial = Serial(ser_port, ser_speed)

    def display_data(self, *args):
        #This doesn't accept a single string, but needs two of them. TODO: make it right.
        for arg in args:
            arg = arg[:self.cols].ljust(self.cols)
        self.serial.write('\n'.join(args))
