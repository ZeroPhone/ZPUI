import smbus
from time import sleep

from input.drivers.skeleton import InputSkeleton

from zpui_lib.helpers import setup_logger
logger = setup_logger(__name__, "warning")

class InputDevice(InputSkeleton):
    """
    An input driver that picks up three side switches from the MCP23008
    on the Blepis LoRa HAT v2.
    """

    default_mapping = [
      "KEY_F5",
      "KEY_F6",
      "KEY_F7",
    ]

    previous_data = 0x00

    def __init__(self, addr = 0x20, bus = 1, int_pin = 4, **kwargs):
        """
        Initialises the ``InputDevice`` object.

        Kwargs:

            * ``bus``: I2C bus number.
            * ``addr``: I2C address of the expander.
            * ``int_pin``: GPIO pin to which INT pin of the expander is connected. If supplied, interrupt-driven mode is used, otherwise, library reverts to polling mode.

        """
        self.bus_num = bus
        self.bus = smbus.SMBus(self.bus_num)
        if isinstance(addr, basestring):
            addr = int(addr, 16)
        self.addr = addr
        self.int_pin = int_pin
        InputSkeleton.__init__(self, **kwargs)

    def init_hw(self):
        """Inits the MCP23008 IC for desired operation."""
        # buttons are on first three bits on v2 of the hat
        # 0. buttons specifically have to be inputs
        # this block is commented out because pins are inputs by default
        # and no other code is assumed to touch them
        """
        pin_state = self.bus.read_byte_data(self.addr, 0x00)
        new_pin_state = pin_state | 0b111 # first three pins have to be 0b111
        self.bus.write_byte_data(self.addr, 0x00, new_pin_state)
        """
        # 1. internal pullups on the buttons
        pin_state = self.bus.read_byte_data(self.addr, 0x06) # GPPU
        new_pin_state = pin_state | 0b111 # first three pins have to be 0b111
        self.bus.write_byte_data(self.addr, 0x06, new_pin_state)
        if self.int_pin != None:
            # 2. interrupts only on the buttons
            pin_state = self.bus.read_byte_data(self.addr, 0x02) # GPINTEN
            new_pin_state = pin_state | 0b111 # first three pins have to be 0b111
            self.bus.write_byte_data(self.addr, 0x02, 0b111)
        self.previous_data = (~self.bus.read_byte_data(self.addr, 0x09)&0b111)
        return True

    def runner(self):
        """Starts either polling or interrupt loop."""
        self.stop_flag = False
        if self.int_pin == None:
            self.loop_polling()
        else:
            self.loop_interrupts()

    def loop_interrupts(self):
        """Interrupt-driven loop. Currently can only use ``RPi.GPIO`` library. Stops when ``stop_flag`` is set to True."""
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
        GPIO.setup(self.int_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        button_states = []
        while not self.stop_flag:
            while GPIO.input(self.int_pin) == False and self.enabled:
                if self.suspended: continue
                data = (~self.bus.read_byte_data(self.addr, 0x09)&0b111)
                self.process_data(data)
                self.previous_data = data
            #logger.debug("eeping")
            sleep(0.1)

    def loop_polling(self):
        """Polling loop. Stops when ``stop_flag`` is set to True."""
        button_states = []
        while not self.stop_flag:
            if self.enabled and not self.suspended:
                data = (~self.bus.read_byte_data(self.addr, 0x09)&0b111)
                if data != self.previous_data:
                    self.process_data(data)
                    self.previous_data = data
            sleep(0.1)

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
