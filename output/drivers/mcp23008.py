import smbus
from time import sleep

from output.output import OutputDevice


def delay(time):
    sleep(time/1000.0)

def delayMicroseconds(time):
    sleep(time/1000000.0)

from hd44780 import HD44780

class Screen(HD44780, OutputDevice):
    """A driver for MCP23008-based I2C LCD backpacks. The one tested had "WIDE.HK" written on it."""

    def __init__(self, bus=1, addr=0x27, debug=False, **kwargs):
        """Initialises the ``Screen`` object.  
                                                                               
        Kwargs:                                                                  
                                                                                 
            * ``bus``: I2C bus number.
            * ``addr``: I2C address of the board.
            * ``debug``: enables printing out LCD commands.
            * ``**kwargs``: all the other arguments, get passed further to HD44780 constructor

        """
        self.bus_num = bus
        self.bus = smbus.SMBus(self.bus_num)
        if type(addr) in [str, unicode]:
            addr = int(addr, 16)
        self.addr = addr
        self.debug = debug
        self.i2c_init()
        HD44780.__init__(self, debug=self.debug, **kwargs)
        
    def i2c_init(self):
        """Inits the MCP23017 IC for desired operation."""
        self.setMCPreg(0x05, 0x0c)
        self.setMCPreg(0x00, 0x00)

    def write_byte(self, byte, char_mode=False):
        """Takes a byte and sends the high nibble, then the low nibble (as per HD44780 doc). Passes ``char_mode`` to ``self.write4bits``."""
        if self.debug and not char_mode:        
            print(hex(byte))                    
        self.write4bits(byte >> 4, char_mode)   
        self.write4bits(byte & 0x0F, char_mode) 

    def write4bits(self, data, char_mode=False):
        """Writes a nibble to the display. If ``char_mode`` is set, holds the RS line high."""
        if char_mode:
            data |= 0x10
        self.setMCPreg(0x0a, data)
        data ^= 0x80
        delayMicroseconds(1.0)
        self.setMCPreg(0x0a, data)
        data ^= 0x80
        delayMicroseconds(1.0)
        self.setMCPreg(0x0a, data)
        delay(1.0)
        
    def setMCPreg(self, reg, val):
        """Sets the MCP23017 register."""
        self.bus.write_byte_data(self.addr, reg, val)


if __name__ == "__main__":
    screen = Screen(bus=1, addr=0x27, cols=16, rows=2, debug=True, autoscroll=False)
    line = "0123456789012345"
    if True:
        screen.display_data(line, line[::-1])
        sleep(1)
        screen.display_data(line[::-1], line)
        sleep(1)
        screen.clear()
