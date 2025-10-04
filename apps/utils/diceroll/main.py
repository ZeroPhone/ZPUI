from zpui_lib.helpers import setup_logger, ExitHelper
from zpui_lib.ui import Canvas
from zpui_lib.apps import ZeroApp

from random import choice
from time import sleep

logger = setup_logger(__name__, "info")

class App(ZeroApp):
    menu_name = "Dice" # App name as seen in main menu while using the system

    def draw_dice(self, c, size=70, start_x=0, start_y=0, value=1):
        r = int(size // 14)
        c.rectangle_wh((start_x, start_y, size, size), fill=c.default_color)
        c_x = int(start_x + size//2); c_y = int(start_y + size//2)
        color = c.background_color
        x1 = c_x - (c_x-start_x)//2; y1 = c_y - (c_y-start_y)//2 # top left circle coordinates
        x2 = c_x + (c_x-start_x)//2; y2 = c_y + (c_y-start_y)//2 # bottom right circle coordinates
        if value in (1, 3, 5): # the center circle
            c.circle((c_x, c_y, r), outline=color, fill=color)
        if value in (2, 3, 4, 5, 6):
            # draw top left and bottom right circles, like this: `-,
            c.circle((x1, y1, r), outline=color, fill=color)
            c.circle((x2, y2, r), outline=color, fill=color)
        if value in (4, 5, 6):
            # now, draw bottom left and top right circles, too
            c.circle((x1, y2, r), outline=color, fill=color)
            c.circle((x2, y1, r), outline=color, fill=color)
        if value == 6:
            # only 6 needs the center-left and center-right circles
            c.circle((x1, c_y, r), outline=color, fill=color)
            c.circle((x2, c_y, r), outline=color, fill=color)

    def on_start(self):
        """This function is called when you click on the app in the main menu"""
        c = Canvas(self.o)
        # let's calculate dice coordinates here
        cx, cy = c.get_center() # cx is centerpoint x, which means it's == width of half of the screen
        # picking the smallest fitting side for our screen, and shrinking it so that there's borders on the sides.
        # For a 320x240 screen, that'll be int(160*0.7)=112, which fits well enough
        dice_size = int(min(self.o.height, cx)*0.7)
        y = (self.o.height-dice_size)//2
        x1 = (cx-dice_size)//2; x2 = x1 + cx
        # we have the coordinates!
        for i in range(11):
            d1 = choice(range(1, 7))
            d2 = choice(range(1, 7))
            self.draw_dice(c, size=dice_size, start_x=x1, start_y=y, value=d1)
            self.draw_dice(c, size=dice_size, start_x=x2, start_y=y, value=d2)
            c.display()
            sleep(0.02)
        self.wait_for_exit()

    def wait_for_exit(self):
        # separated out so that the app code can be tested
        eh = ExitHelper(self.i).start()
        while eh.do_run():
            sleep(0.1)

################################################
#
# remember - if you're stuck building something,
# ask me all the questions!
# I'm here to try and help you.
#
################################################


"""
TESTS

Here you can test your app's features or sub-features.
"""

class TestedApp(App):
    """
    A stubbed version of the app, so that internal functions can be tested without substituting a lot of ZPUI input/output code.
    """
    def __init__(self):
        from zpui_lib.ui import MockOutput
        self._ZeroApp__output = MockOutput(width=320, height=240, warn_on_display=False)
    # substitute other functions here as needed for testing

    def wait_for_exit(self):
        pass # omitting the waiting-on-input part


import unittest
class Tests(unittest.TestCase):
    def test_simple(self):
        """Simple test. Runs the app and checks if the app code errors out."""
        # todo: maybe mock out the `sleep` function to avoid delays in running the test?
        app = TestedApp()
        app.on_start()

if __name__ == "__main__":
    unittest.main()

