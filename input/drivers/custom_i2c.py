import smbus
from time import sleep

from helpers import setup_logger
from input.drivers.skeleton import InputSkeleton, KEY_PRESSED, KEY_RELEASED, KEY_HELD
logger = setup_logger(__name__, "warning")

class InputDevice(InputSkeleton):
    default_mapping = [
    "KEY_LEFT",
    "KEY_UP",
    "KEY_DOWN",
    "KEY_RIGHT",
    "KEY_ENTER",
    "KEY_1",
    "KEY_2",
    "KEY_3",
    "KEY_4",
    "KEY_5",
    "KEY_6",
    "KEY_7",
    "KEY_8",
    "KEY_9",
    "KEY_*",
    "KEY_0",
    "KEY_#",
    "KEY_F1",
    "KEY_F2",
    "KEY_ANSWER",
    "KEY_HANGUP",
    "KEY_F3",
    "KEY_F4",
    "KEY_F5",
    "KEY_F6",
    "KEY_VOLUMEUP",
    "KEY_VOLUMEDOWN",
    "KEY_PROG1",
    "KEY_PROG2",
    "KEY_CAMERA"
    ]

    status_available = True
    supports_key_states = True
    supports_held_state = True
    state_mapping = {0:KEY_PRESSED, 1:KEY_HELD, 2:KEY_RELEASED}

    def __init__(self, addr = 0x12, bus = 1, int_pin = 16, **kwargs):
        """Initialises the ``InputDevice`` object.

        Kwargs:

            * ``bus``: I2C bus number.
            * ``addr``: I2C address of the device.
            * ``int_pin``: GPIO pin for interrupt mode.

        """
        self.bus_num = bus
        if isinstance(addr, basestring):
            addr = int(addr, 16)
        self.addr = addr
        self.int_pin = int_pin
        InputSkeleton.__init__(self, **kwargs)

    def init_hw(self):
        self.bus = smbus.SMBus(self.bus_num)
        self.bus.read_byte(self.addr)
        return True

    def runner(self):
        """Runs either interrupt-driven or polling loop."""
        self.stop_flag = False
        if self.int_pin is None:
            self.loop_polling() # Actually... it's not implemented =D
        else:
            self.loop_interrupts()

    def loop_interrupts(self):
        """Interrupt-driven loop. Currently can only use ``RPi.GPIO`` library. Stops when ``stop_flag`` is set to True."""
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
        GPIO.setup(self.int_pin, GPIO.IN)
        while not self.stop_flag:
            if not self.check_connection():
                # Looping while the device is not found
                sleep(self.connection_check_sleep)
                continue
            while GPIO.input(self.int_pin) == False and self.enabled:
                logger.debug("GPIO low, reading data")
                try:
                    data = self.bus.read_byte(self.addr)
                    logger.debug("Received {:#010b}".format(data))
                except IOError:
                    if self.connected.isSet():
                        logger.error("Can't get data from keypad!")
                        self.connected.clear()
                else:
                    if not self.connected.isSet():
                        logger.info("Receiving data from keypad again!")
                        self.connected.set()
                    # Valid format: 8 bits
                    # [0, state, state, key, key, key, key, key]
                    # Parsing data into bits
                    data_7 = data >> 7           # Bit  7
                    data_65 = (data >> 5) & 0x7  # Bits 6 and 5
                    data_43210 = data & 0x1f     # Bits 4,3,2,1,0
                    #print("{} {} {} {}".format( *map(bin, (data, data_7, data_65, data_43210)) ))
                    if data_7 == 0 \
                      and data_65 in self.state_mapping.keys() \
                      and data_43210 != 0:
                        # data_7 should be 0, other reserved for future
                        # data_65 in (0, 1, 2): (pressed, released, held), 3 is reserved
                        # data_43210 != 0: 0x00 is returned when I2C buffer is empty (no keys to be read)
                        key_num = data_43210 - 1
                        if key_num in range(len(self.mapping)):
                            key_name = self.mapping[key_num]
                            state = data_65
                            logger.debug("Maps to valid key: {}, state: {}".format(key_name, state))
                            self.map_and_send_key(key_name, state=self.state_mapping[state])
                        else:
                            logger.warning("Non-mappable key data arrived: {}".format(key_num))
                    else:
                        if data == 0:
                            logger.warning("Received 0 or other data from keypad though the interrupt has been triggered!")
                            sleep(0.1)
                        else:
                            logger.info("Non-key data arrived: {}".format(bin(data)))
            sleep(0.1)


if __name__ == "__main__":
    id = InputDevice(addr = 0x12, int_pin = 16, threaded=False)
    id.runner()
