import smbus
from time import sleep

from input.drivers.skeleton import InputSkeleton

class InputDevice(InputSkeleton):
    """ A driver for MAX7318-based I2C IO expanders. They have 16 IO pins available as well as an interrupt pin. 
    This driver treats all 16 pins as button pins, which is the case in my latest project.

    It supports both interrupt-driven mode (as for now, RPi-only due to RPi.GPIO library used) and polling mode."""

    default_mapping = [
    "KEY_LEFT",
    "KEY_UP",
    "KEY_DOWN",
    "KEY_RIGHT",
    "KEY_ENTER",
    "KEY_0",
    "KEY_1",
    "KEY_2",
    "KEY_3",
    "KEY_4",
    "KEY_5",
    "KEY_6",
    "KEY_7",
    "KEY_8",
    "KEY_9",
    "KEY_DELETE"]

    previous_data = 0x00

    def __init__(self, addr = 0x20, bus = 1, int_pin = None, **kwargs):
        """Initialises the ``InputDevice`` object.  
                                                                               
        Kwargs:                                                                  
                                                                                 
            * ``bus``: I2C bus number.
            * ``addr``: I2C address of the expander.
            * ``int_pin``: GPIO pin to which INT pin of the expander is connected. If supplied, interrupt-driven mode is used, otherwise, library reverts to polling mode.

        """
        self.bus_num = bus
        self.bus = smbus.SMBus(self.bus_num)
        if type(addr) in [str, unicode]:
            addr = int(addr, 16)
        self.addr = addr
        self.int_pin = int_pin
        self.init_expander()
        InputSkeleton.__init__(self, **kwargs)

    def init_expander(self):
        #Now setting previous_data to a sensible value (assuming no buttons are pressed on init)
        try:
            data0 = (~self.bus.read_byte_data(self.addr, 0x00)&0xFF)
            data1 = (~self.bus.read_byte_data(self.addr, 0x01)&0xFF)
            self.previous_data = data0 | (data1 << 8) 
        except IOError:
            return False
        return True

    def runner(self):
        """Starts either polling or interrupt loop."""
        self.stop_flag = False
        if self.int_pin is None:
            self.loop_polling()
        else:
            self.loop_interrupts()

    def loop_interrupts(self):
        """Interrupt-driven loop. Currently can only use ``RPi.GPIO`` library. Stops when ``stop_flag`` is set to True."""
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
        GPIO.setup(self.int_pin, GPIO.IN)
        button_states = []
        while not self.stop_flag:
            while GPIO.input(self.int_pin) == False and self.enabled:
                data0 = (~self.bus.read_byte_data(self.addr, 0x00)&0xFF)
                data1 = (~self.bus.read_byte_data(self.addr, 0x01)&0xFF)
                data = data0 | (data1 << 8) 
                self.process_data(data)
                self.previous_data = data
            sleep(0.01)

    def loop_polling(self):
        """Polling loop. Stops when ``stop_flag`` is set to True."""
        button_states = []
        while not self.stop_flag:
            if self.enabled:
                data0 = (~self.bus.read_byte_data(self.addr, 0x00)&0xFF)
                data1 = (~self.bus.read_byte_data(self.addr, 0x01)&0xFF)
                data = data0 | (data1 << 8) 
                if data != self.previous_data:
                    self.process_data(data)
                    self.previous_data = data
            sleep(0.01)

    def process_data(self, data):
        """Checks data received from IO expander and classifies changes as either "button up" or "button down" events. On "button up", calls send_key with the corresponding button name from ``self.mapping``. """
        data_difference = data ^ self.previous_data
        changed_buttons = []
        for i in range(len(self.mapping)):
            if data_difference & 1<<i:
                changed_buttons.append(i)
        for button_number in changed_buttons:
            if not data & 1<<button_number:
                self.send_key(self.mapping[button_number])


if __name__ == "__main__":
    id = InputDevice(int_pin = 4, threaded=False)
    id.runner()
