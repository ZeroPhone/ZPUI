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

    type = ["char", "rgb_led"]

    def __init__(self, bus=1, addr=0x20, debug=False, chinese=True, **kwargs):
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
        self.chinese = chinese
        self.i2c_init()
        BacklightManager.init_backlight(self, **kwargs)
        HD44780.__init__(self, debug=self.debug, **kwargs)
        
    def i2c_init(self):
        """Inits the MCP23017 expander."""
        self.setMCPreg(0x00, 0x00)
        self.setMCPreg(0x01, 0x00)

    @activate_backlight_wrapper
    def write_byte(self, byte, char_mode=False):
        """Takes a byte and sends the high nibble, then the low nibble (as per HD44780 doc). Passes ``char_mode`` to ``self.write4bits``."""
        if self.debug and not char_mode:        
            print(hex(byte))                    
        self.write4bits(byte >> 4, char_mode)   
        self.write4bits(byte & 0x0F, char_mode) 

    @enable_backlight_wrapper
    def enable_backlight(self):
        """Enables backlight. Doesn't do it instantly on genuine boards, you'll have to wait until data is sent to the display."""
        if self.chinese: 
            self.setMCPreg(0x14, 0xc0) 
        else:
            self.setMCPreg(0x14, 0xe0)

    @disable_backlight_wrapper
    def disable_backlight(self):
        """Disables backlight. Doesn't do it instantly on genuine boards, you'll have to wait until data is sent to the display."""
        if self.chinese: 
            self.setMCPreg(0x14, 0xe0) 
        else:
            self.setMCPreg(0x15, 0x01)

    def write4bits(self, data, char_mode=False):
        """Writes a nibble to the display. If ``char_mode`` is set, holds the RS line high."""
        data = int('{:04b}'.format(data)[::-1], 2) #Reversing data since on Adafruit shields DB7=GP1, DB6=GP2 and so on
        data = data << 1 #Need to also shift it to one bit
        if char_mode:
            data |= 0x80
        if self.chinese or not self._backlight_enabled:
                data |= 0x01 #Chinese boards have a blue LED instead of Adafruit backlight pin, this turns blue LED off =)
                #Adafruit boards have blue backlight at GP0, and we set the bit to turn the backlight off
        self.setMCPreg(0x15, data)
        data ^= 0x20
        self.setMCPreg(0x15, data)
        data ^= 0x20
        self.setMCPreg(0x15, data)
        
    def setMCPreg(self, reg, val):
        """Sets the MCP23017 register."""
        self.bus.write_byte_data(self.addr, reg, val)

    def set_rgb(self, red, green, blue):
        port_a = 0 | ((not green) << 7)
        port_a |= ((not red) << 6)
        if self.chinese: 
            port_a |= ((not self._backlight_enabled) << 5)
            self.setMCPreg(0x14, port_a) 
            self.setMCPreg(0x15, ((not blue) << 0))
        else:
            port_a |= ((not blue) << 5)
            self.setMCPreg(0x14, port_a)

if __name__ == "__main__":
    screen = Screen(bus=1, addr=0x20, cols=16, rows=2, debug=True, chinese=True)
    line = "0123456789012345"
    """if True:
        screen.display_data(line, line[::-1])
        sleep(1)
        screen.disable_backlight()
        screen.display_data(line[::-1], line)
        sleep(1)
        screen.clear()"""
    screen.set_rgb(1, 1, 1)
    sleep(1)
    screen.set_rgb(0, 0, 0)
    sleep(1)
    screen.set_rgb(1, 0, 0)
    sleep(1)
    screen.set_rgb(0, 1, 0)
    sleep(1)
    screen.set_rgb(0, 0, 1)
    sleep(1)
    screen.set_rgb(0, 0, 0) 
