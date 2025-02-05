from time import sleep

from input.drivers.skeleton import InputSkeleton, KEY_PRESSED, KEY_RELEASED

class InputDevice(InputSkeleton):
    """ A driver for pushbuttons attached to Raspberry Pi GPIO.
    It uses RPi.GPIO library. Button's first pin has to be attached
    to ground, second pin has to be attached to the GPIO pin. Pullups
    are expected - by default, internal pullups of Raspberry Pi GPIO
    are enabled. If internal pullups are not desired, supply
    `"pullups":false` in config.json and provide your own pullups."""

    supports_key_states = True
    supports_held_state = False

    default_mapping = [
    "KEY_UP",
    "KEY_DOWN",
    "KEY_LEFT",
    "KEY_RIGHT",
    "KEY_ENTER",
    "KEY_F3",
    "KEY_F4",
    "KEY_PROG1"]

    def __init__(self, button_pins=[], pullups=True, **kwargs):
        """Initialises the ``InputDevice`` object.

        Kwargs:

        * ``button_pins``: GPIO numbers which to treat as buttons (GPIO.BCM numbering)
        * ``pullups``: if True, enables pullups on all pins, if False, doesn't. Default: True
        * ``debug``: enables printing button press and release events when set to True
        """
        self.button_pins = button_pins
        self.pullups = pullups
        InputSkeleton.__init__(self, **kwargs)

    def init_hw(self):
        import RPi.GPIO as GPIO #Doing that because I couldn't mock it for ReadTheDocs
        self.GPIO = GPIO
        GPIO.setmode(GPIO.BCM)
        for pin_num in self.button_pins:
            if self.pullups:
                GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(pin_num, GPIO.IN)
        self.button_states = []
        for i, pin_num in enumerate(self.button_pins):
            self.button_states.append(GPIO.input(pin_num))
        return None # Status not available

    def runner(self):
        """Polling loop. Stops when ``stop_flag`` is set to True."""
        while not self.stop_flag:
            for i, pin_num in enumerate(self.button_pins):
                button_state = self.GPIO.input(pin_num)
                if button_state != self.button_states[i]:
                    if self.enabled:
                        key = self.mapping[i]
                        state = KEY_RELEASED if button_state else KEY_PRESSED
                        self.map_and_send_key(key, state=state)
                    self.button_states[i] = button_state
            sleep(0.01)



if __name__ == "__main__":
    id = InputDevice(button_pins=[22, 23, 27, 24, 18, 4], threaded=False)
    id.runner()
