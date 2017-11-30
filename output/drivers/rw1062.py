import smbus
from time import sleep

from output.output import OutputDevice


def delay(time):
    sleep(time/1000.0)

def delayMicroseconds(time):
    sleep(time/1000000.0)

from hd44780 import HD44780
from backlight import *

class Screen(HD44780, BacklightManager, OutputDevice):
    """A driver for Adafruit-developed Raspberry Pi character LCD&button shields based on MCP23017, either Adafruit-made or Chinese-made.
       Has workarounds for Chinese plates with LED instead of RGB backlight and LCD backlight on a separate I2C GPIO expander pin.
       
       Tested on hardware compatible with Adafruit schematic and working with Adafruit libraries, but not on genuine Adafruit hardware. Thus, you may have issues with backlight, as that's the 'gray area'.
    """

    def __init__(self, bus=1, addr=0x20, debug=False, **kwargs):
        """Initialises the ``Screen`` object.  
                                                                               
        Kwargs:                                                                  
                                                                                 
            * ``bus``: I2C bus number.
            * ``addr``: I2C address of the board.
            * ``debug``: enalbes printing out LCD commands.
            * ``chinese``: flag enabling workarounds necessary for Chinese boards to enable LCD backlight.

        """
        self.bus_num = bus
        self.bus = smbus.SMBus(self.bus_num)
        if type(addr) in [str, unicode]:
            addr = int(addr, 16)
        self.addr = addr
        self.debug = debug
        BacklightManager.init_backlight(self, **kwargs)
        HD44780.__init__(self, debug=self.debug, **kwargs)
        
    def init_display(self, **kwargs):
        self.bus.write_byte_data(self.addr, 0x00, 0x30)
        delay(1)
        self.bus.write_byte_data(self.addr, 0x00, 0x30)
        delay(1)
        self.bus.write_byte_data(self.addr, 0x00, 0x08)
        delay(1)
        self.bus.write_byte_data(self.addr, 0x00, 0x06)
        delay(1)
        self.bus.write_byte_data(self.addr, 0x01, 0x34)
        delay(10)
        self.bus.write_byte_data(self.addr, 0x01, 0x02)
        delay(100)
        self.bus.write_byte_data(self.addr, 0x01, 0x06)
        delay(100)
        self.bus.write_byte_data(self.addr, 0x01, 0x16)
        delay(100)
        self.bus.write_byte_data(self.addr, 0x01, 0x08)
        delay(100)
        self.bus.write_byte_data(self.addr, 0x01, 0x08)
        delay(100)
        self.bus.write_byte_data(self.addr, 0x00, 0x30)
        delay(1)
        self.bus.write_byte_data(self.addr, 0x00, 0x0c)
        delay(1)
        self.clear()
 
    def println(self, line):
        self.bus.write_i2c_block_data(self.addr, 0x40, [ord(char) for char in line])

    @activate_backlight_wrapper
    def write_byte(self, data, char_mode=False):
	if char_mode:
            self.bus.write_byte_data(self.addr, 0x40, data)
	else:
            self.bus.write_byte_data(self.addr, 0x00, data)
	

if __name__ == "__main__":
    screen = Screen(bus=1, addr=0x3c, cols=24, rows=2, debug=True)
    line = "012345678901234567890123"
    if True:
        screen.display_data(line, line[::-1])
        sleep(1)
        screen.display_data(line[::-1], line)
        sleep(1)
        screen.clear()
