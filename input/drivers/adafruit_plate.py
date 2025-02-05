import smbus
from time import sleep

from input.drivers.skeleton import InputSkeleton

class InputDevice(InputSkeleton):
    """A driver for Adafruit-developed Raspberry Pi character LCD&button shields based on MCP23017, either Adafruit-made or Chinese-made.
 
       Tested on hardware compatible with Adafruit schematic and working with Adafruit libraries, but not on genuine Adafruit hardware. 
    """
    default_mapping = [
    "KEY_ENTER",
    "KEY_RIGHT",
    "KEY_DOWN",
    "KEY_UP",
    "KEY_LEFT"]

    previous_data = 0

    def __init__(self, addr = 0x20, bus = 1, **kwargs):
        """Initialises the ``InputDevice`` object.  
                                                                               
        Kwargs:                                                                  
                                                                                 
            * ``bus``: I2C bus number.
            * ``addr``: I2C address of the expander.

        """
        self.bus_num = bus
        self.bus = smbus.SMBus(self.bus_num)
        if type(addr) in [str, unicode]:
            addr = int(addr, 16)
        self.addr = addr
        self.init_expander()
        InputSkeleton.__init__(self, **kwargs)

    def init_expander(self):
        """Initialises the IO expander."""
        self.setMCPreg(0x00, 0x1F)
        self.setMCPreg(0x0C, 0x1F)

    def runner(self):
        """Polling loop (only one there can be on this shield, since interrupt pin is not connected)."""
        button_states = []
        while not self.stop_flag:
            if self.enabled:
                data = (~self.readMCPreg(0x12)&0x1F)
                if data != self.previous_data:
                    self.process_data(data)
                    self.previous_data = data
            sleep(0.01)

    def process_data(self, data):
        """Checks data received from IO expander and classifies changes as either "button up" or "button down" events. On "button up", calls send_key with the corresponding button name from ``self.mapping``. """
        data_difference = data ^ self.previous_data
        changed_buttons = []
        for i in range(8):
            if data_difference & 1<<i:
                changed_buttons.append(i)
        for button_number in changed_buttons:
            if not data & 1<<button_number:
                self.send_key(self.mapping[button_number])

    def setMCPreg(self, reg, val):
        """Sets the MCP23017 register."""
        self.bus.write_byte_data(self.addr, reg, val)

    def readMCPreg(self, reg):
        """Reads the MCP23017 register."""
        return self.bus.read_byte_data(self.addr, reg)


if __name__ == "__main__":
    id = InputDevice(addr = 0x20, threaded=False)
    id.runner()
