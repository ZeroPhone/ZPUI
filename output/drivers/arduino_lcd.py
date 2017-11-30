from serial import Serial
from time import sleep

#Firmware: TODO
from output.output import OutputDevice


def delay(time):
    sleep(time/1000.0)

def delayMicroseconds(time):
    sleep(time/1000000.0)

from hd44780 import HD44780

class Screen(HD44780, OutputDevice):
    """A driver for MCP23008-based I2C LCD backpacks. The one tested had "WIDE.HK" written on it."""

    def __init__(self, port=None, speed=9600, debug=False **kwargs):
        """Initialises the ``Screen`` object.  
                                                                               
        Kwargs:                                                                  
                                                                                 
            * ``port``: serial port path
            * ``speed``: serial port speed
            * ``debug``: enables printing out LCD commands.
            * ``**kwargs``: all the other arguments, get passed further to HD44780 constructor

        """
        self.port_path = port
        self.speed = speed
        self.port = Serial(self.port_path, self.speed)
        self.debug = debug
        HD44780.__init__(self, debug=self.debug, **kwargs)
        
    def write_byte(self, byte, char_mode=False):
        """Takes a byte and sends the high nibble, then the low nibble (as per HD44780 doc). Passes ``char_mode`` to ``self.write4bits``."""
        if self.debug and not char_mode:        
            print(hex(byte))
        if char_mode:                    
            self.serial.write(str(bytearray([0xfe, byte])))
        else:
            self.serial.write(byte)
        

if __name__ == "__main__":
    screen = Screen(bus=1, addr=0x27, cols=16, rows=2, debug=True, autoscroll=False)
    line = "0123456789012345"
    if True:
        screen.display_data(line, line[::-1])
        sleep(1)
        screen.display_data(line[::-1], line)
        sleep(1)
        screen.clear()



