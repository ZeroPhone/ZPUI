import threading
import pifacecad

from time import sleep

from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "warning")

class InputDevice(object):
    """ A driver for PiFace Control and Display Raspberry Pi shields. It has 5 buttons, one single-axis joystick with a pushbutton, a 16x2 HD44780 screen and an IR receiver (not used yet)."""
    mapping = [
    "KEY_LEFT",
    "KEY_RIGHT",
    "KEY_HOME",
    "KEY_END",
    "KEY_DELETE",
    "KEY_ENTER",
    "KEY_UP",
    "KEY_DOWN"]
    stop_flag = False
    previous_data = 0
    
    def __init__(self):
        """Initialises the ``InputDevice`` object and starts ``pifacecad.SwitchEventListener``. Also, registers callbacks to ``press_key`` method. """
        self.cad = pifacecad.PiFaceCAD()
    
    def start(self):
        """Starts listening on the input device. Initialises the IO expander and runs either interrupt-driven or polling loop."""
        self.stop_flag = False
        self.loop_polling()

    def loop_polling(self):
        """Polling loop. Stops when ``stop_flag`` is set to True."""
        button_states = []
        while not self.stop_flag:
            if self.suspended: sleep(0.01); continue
            data = self.cad.switch_port.value
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

    def send_key(self, keycode):
        """A hook to be overridden by ``InputListener``. Otherwise, prints out key names as soon as they're pressed so is useful for debugging."""
        logger.info(keycode)

    def stop(self):
        """Sets the ``stop_flag`` for loop function."""
        self.stop_flag = True

    def activate(self):
        """Starts a thread with ``start`` function as target."""
        self.thread = threading.Thread(target=self.start)
        self.thread.daemon = False
        self.thread.start()

    def deactivate(self):
        """Starts a thread with ``start`` function as target."""
        self.thread.stop()

if __name__ == "__main__":
    id = InputDevice()
    id.start()
