import smbus
from time import sleep

from input.drivers.skeleton import InputSkeleton

class InputDevice(InputSkeleton):
    """ A driver for PCF8574-based I2C IO expanders. They have 8 IO pins available as well as an interrupt pin. This driver treats all 8 pins as button pins, which is often the case. 

    It supports both interrupt-driven mode (as fr now, RPi-only) and polling mode."""

    default_mapping = [
    "KEY_ENTER",
    "KEY_DELETE",
    "KEY_END",
    "KEY_DOWN",
    "KEY_UP",
    "KEY_HOME",
    "KEY_LEFT",
    "KEY_RIGHT"]

    previous_data = 0

    def __init__(self, addr = 0x27, bus = 1, int_pin = None, **kwargs):
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
        try:
            self.bus.write_byte(self.addr, 0xff)
        except IOError:
            return True
        else:
            return False

    def runner(self):
        """Starts listening on the input device. Initialises the IO expander and runs either interrupt-driven or polling loop."""
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
                data = (~self.bus.read_byte(self.addr)&0xFF)
                self.process_data(data)
                self.previous_data = data
            sleep(0.1)

    def loop_polling(self):
        """Polling loop. Stops when ``stop_flag`` is set to True."""
        button_states = []
        while not self.stop_flag:
            if self.enabled:
                data = (~self.bus.read_byte(self.addr)&0xFF)
                if data != self.previous_data:
                    self.process_data(data)
                    self.previous_data = data
            sleep(0.1)

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


if __name__ == "__main__":
    id = InputDevice(addr = 0x23, threaded=False)
    id.runner()
