from time import sleep

from input.drivers.skeleton import InputSkeleton

class InputDevice(InputSkeleton):

    default_mapping = [
    ["KEY_1", "KEY_UP", "KEY_3"],
    ["KEY_LEFT", "KEY_ENTER", "KEY_RIGHT"],
    ["KEY_7", "KEY_DOWN", "KEY_9"],
    ["KEY_*", "KEY_0", "KEY_#"]]

    def __init__(self, cols=[5, 6, 13], rows=[12, 16, 20, 21], **kwargs):
        """Initialises the ``InputDevice`` object.

        Kwargs:

        * ``button_pins``: GPIO mubers which to treat as buttons (GPIO.BCM numbering)
        * ``debug``: enables printing button press and release events when set to True
        """
        self.cols = cols
        self.rows = rows
        InputSkeleton.__init__(self, **kwargs)

    def set_available_keys(self):
        # mapping needs to be flattened before we can get available_keys from it
        self.available_keys = [item for row in self.mapping for item in row]

    def init_hw(self):
        import RPi.GPIO as GPIO #Doing that because I couldn't mock it for ReadTheDocs
        self.GPIO = GPIO
        GPIO.setmode(GPIO.BCM)
        for pin_num in self.rows:
            GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        for pin_num in self.cols:
            GPIO.setup(pin_num, GPIO.OUT)
            GPIO.output(pin_num, True)
        self.button_states = [[False for u in range(len(self.cols))] for i in range(len(self.rows))]
        return None # Status reading not available

    def runner(self):
        """Polling loop. Stops when ``stop_flag`` is set to True."""
        while not self.stop_flag:
            for row_num, row_pin in enumerate(self.rows):
                prev_row_state = self.button_states[row_num]
                if self.GPIO.input(row_pin) != any(prev_row_state):
                    for col in self.cols: self.GPIO.output(col, False)
                    #A button pressed!
                    col_num = None
                    for col_num, col_pin in enumerate(self.cols):
                        self.GPIO.output(col_pin, True)
                        state = self.GPIO.input(row_pin)
                        self.GPIO.output(col_pin, False)
                        prev_state = self.button_states[row_num][col_num]
                        if state == True and prev_state == False:
                            key = self.mapping[row_num][col_num]
                            self.map_and_send_key(key)
                        self.button_states[row_num][col_num] = state
                    for col in self.cols: self.GPIO.output(col, True)
            sleep(0.01)



if __name__ == "__main__":
    id = InputDevice(threaded=False)
    id.runner()
