from time import sleep

from input.drivers.skeleton import InputSkeleton

class InputDevice(InputSkeleton):
    default_mapping = [
    "KEY_LEFT",
    "KEY_UP",
    "KEY_DOWN",
    "KEY_RIGHT",
    "KEY_ENTER"]

    def __init__(self, **kwargs):
        """Initialises the ``InputDevice`` object - basically, does nothing. """
        InputSkeleton.__init__(self, **kwargs)

    def init_hw(self):
        return True

    def runner(self):
        """Test loop runner"""
        self.stop_flag = False
        self.loop_polling()

    def loop_polling(self):
        """Test loop"""
        while not self.stop_flag:
            while self.enabled:
                sleep(0.1)

if __name__ == "__main__":
    id = InputDevice(threaded=False)
    id.runner()
