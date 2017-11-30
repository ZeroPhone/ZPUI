import pifacecad
from time import sleep

from output.output import OutputDevice


class Screen(OutputDevice):
    """ A driver for PiFace Control and Display Raspberry Pi shields. It has a simple 16x2 LCD on it, controlled by a MCP23S17 over SPI.

    Doesn't yet conform to HD44780 library specs, many functions are not transferred from the ``pifacecad`` library.

    TODO: rewrite it to remove dependency on PiFaceCAD library."""

    type = ["char"] #For future compatibility with graphical displays

    def __init__(self, rows=2, cols=16):
        """Initialises the ``Screen`` object.  
                                                                               
        Kwargs:

           * ``rows`` (default=2): rows of the connected display
           * ``cols`` (default=16): columns of the connected display

        """
        self.rows = rows
        self.cols = cols
        self.lcd = pifacecad.PiFaceCAD().lcd
        self.backlight = True
        self.busy_flag = False

    def enable_backlight(self): 
        """Enables backlight. Doesn't do it instantly, you'll have to wait until data is sent to the display."""
        self.backlight = True

    def disable_backlight(self):
        """Disables backlight."""
        self.backlight = False
        self.lcd.backlight_off()

    def clear(self):
        """Clears the display."""
        self.lcd.clear()

    def display_data(self, *args):
        """Displays data on display.
        
        ``*args`` is a list of strings, where each string fills each row of the display, starting with 0."""
        while self.busy_flag:
            sleep(0.01)
        self.busy_flag = False
        self.lcd.blink_off()
        self.lcd.cursor_off()
        if self.backlight:
            self.lcd.backlight_on() 
        self.lcd.clear()
        for arg in args:
            arg = arg[:self.cols].ljust(self.cols)
        self.lcd.write('\n'.join(args))
        self.busy_flag = False


if __name__ == "__main__":
    screen = Screen()
    line = "0123456789012345"
    if True:
        screen.display_data(line, line[::-1])
        sleep(1)
        screen.disable_backlight()
        screen.display_data(line[::-1], line)
        sleep(1)
        screen.clear()

