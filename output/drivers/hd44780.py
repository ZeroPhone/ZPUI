#!/usr/bin/python

#
# based on code from Adafruit, lrvick and LiquidCrystal
# lrvick - https://github.com/lrvick/raspi-hd44780/blob/master/hd44780.py
# LiquidCrystal - https://github.com/arduino/Arduino/blob/master/libraries/LiquidCrystal/LiquidCrystal.cpp
# Adafruit - https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code
#

from time import sleep

def delayMicroseconds(microseconds):
    seconds = microseconds / float(1000000)  # divide microseconds by 1 million for seconds
    sleep(seconds)

def delay(milliseconds):
    seconds = milliseconds / float(1000)  # divide microseconds by 1 million for seconds
    sleep(seconds)

try:
    from ..output import CharacterOutputDevice
except ModuleNotFoundError:
    from output import CharacterOutputDevice

class HD44780(object):
    """An object that provides high-level functions for interaction with display. It contains all the high-level logic and exposes an interface for system and applications to use."""

    # commands
    LCD_CLEARDISPLAY        = 0x01
    LCD_RETURNHOME          = 0x02
    LCD_ENTRYMODESET        = 0x04
    LCD_DISPLAYCONTROL      = 0x08
    LCD_CURSORSHIFT         = 0x10
    LCD_FUNCTIONSET         = 0x20
    LCD_SETCGRAMADDR        = 0x40
    LCD_SETDDRAMADDR        = 0x80

    # flags for display entry mode
    LCD_ENTRYRIGHT          = 0x00
    LCD_ENTRYLEFT           = 0x02
    LCD_ENTRYSHIFTINCREMENT = 0x01
    LCD_ENTRYSHIFTDECREMENT = 0x00

    # flags for display on/off control
    LCD_DISPLAYON           = 0x04
    LCD_DISPLAYOFF          = 0x00
    LCD_CURSORON            = 0x02
    LCD_CURSOROFF           = 0x00
    LCD_BLINKON             = 0x01
    LCD_BLINKOFF            = 0x00

    # flags for display/cursor shift
    LCD_DISPLAYMOVE         = 0x08
    LCD_CURSORMOVE          = 0x00

    # flags for display/cursor shift
    LCD_DISPLAYMOVE         = 0x08
    LCD_CURSORMOVE          = 0x00
    LCD_MOVERIGHT           = 0x04
    LCD_MOVELEFT            = 0x00

    # flags for function set
    LCD_8BITMODE            = 0x10
    LCD_4BITMODE            = 0x00
    LCD_2LINE               = 0x08
    LCD_1LINE               = 0x00
    LCD_5x10DOTS            = 0x04
    LCD_5x8DOTS             = 0x00

    row_offsets = [0x00, 0x40, 0x14, 0x54]

    display_function = LCD_FUNCTIONSET | LCD_4BITMODE | LCD_2LINE | LCD_5x8DOTS
    displaycontrol = 0x0c
    displaymode = 0x07

    busy_flag = False
    buffer = " "

    redraw_coefficient = 0.5
    type = ["char"] #Variable for future compatibility with graphical displays

    __base_classes__ = (CharacterOutputDevice, )

    def __init__(self, cols = 16, rows=2, do_init = True, debug = False, buffering = True, **kwargs):
        """ Sets variables for high-level functions.
        
        Kwargs:

           * ``rows`` (default=2): rows of the connected display
           * ``cols`` (default=16): columns of the connected display
           * ``debug`` (default=False): debug mode which prints out the commands sent to display
           * ``**kwargs``: all the other arguments, get passed further to HD44780.init_display() function"""
        self.cols = cols
        self.rows = rows
        self.debug = debug
        self.buffering = buffering
        if self.buffering: #Init the buffer
            self.buffer = [" "*self.cols for i in range(self.rows)]
        if do_init:
            self.init_display(**kwargs)

    def init_display(self, autoscroll=False, **kwargs):
        """Initializes HD44780 controller. 

        Kwargs:
        
        * ``autoscroll``: Controls whether autoscroll-on-char-print is enabled upon initialization. 
        """
        self.write_byte(0x30)  # initialization
        delay(20)
        self.write_byte(0x30)  # initialization
        delay(20)
        self.write_byte(0x30)  # initialization
        delay(20)
        self.home()
        self.write_byte(self.display_function)
        self.noDisplay()
        if autoscroll:
            self.autoscroll()
        else:
            self.noAutoscroll()
        self.clear()
        self.display()

    def display_data(self, *args):
        """Displays data on display. This function checks if the display contents can be redrawn faster by buffering them and checking the output, then either changes characters one-by-one or redraws the screen completely.
        
        ``*args`` is a list of strings, where each string corresponds to a row of the display, starting with 0."""
        #Formatting the args list to simplify the processing
        args = list(args[:self.rows]) #Cut it to our max length and convert to list so we can change it
        for i, string in enumerate(args): #Pad each string
            args[i] = string[:self.cols].ljust(self.cols)
        if len(args) < self.rows: #Pad with empty strings if it's not yet padded
            for i in range(self.rows-len(args)): 
                args.append(" "*self.cols)
        diffs = [[] for i in range(self.rows)]
        for i, string in enumerate(args):
            for j, char in enumerate(string):
                if self.buffer[i][j] != char:
                    diffs[i].append(j)
        if float(sum([len(diff) for diff in diffs]))/(self.rows*self.cols) > self.redraw_coefficient:
            self._display_data(*args) #Redrawing the display
            self.buffer = args
        else:
            for row_num, row_diffs in enumerate(diffs):
                for i, char_cpos in enumerate(row_diffs):
                    self.setCursor(row_num, char_cpos)
                    self.write_byte(ord(args[row_num][char_cpos]), char_mode=True)
            self.buffer = args

    def _display_data(self, *args):
        """Displays data on display. This function does the actual work of printing things to display.
        
        ``*args`` is a list of strings, where each string corresponds to a row of the display, starting with 0."""
        while self.busy_flag:
            sleep(0.01)
        self.busy_flag = True
        self.clear()
        args = args[:self.rows]
        for line, arg in enumerate(args):
            self.setCursor(line, 0)
            self.println(arg[:self.cols].ljust(self.cols))
        self.busy_flag = False

    def println(self, line):
        """Prints a line on the screen (assumes position is set as intended)"""
        for char in line:
            self.write_byte(ord(char), char_mode=True)     

    def home(self):
        """Returns cursor to home position. If the display is being scrolled, reverts scrolled data to initial position.."""
        self.write_byte(self.LCD_RETURNHOME)  # set cursor position to zero
        delayMicroseconds(3000)  # this command takes a long time!

    def clear(self):
        """Clears the display."""
        self.write_byte(self.LCD_CLEARDISPLAY)  # command to clear display
        delayMicroseconds(3000)  # 3000 microsecond sleep, clearing the display takes a long time

    def setCursor(self, row, col):
        """ Set current input cursor to ``row`` and ``column`` specified """
        self.write_byte(self.LCD_SETDDRAMADDR | (col + self.row_offsets[row]))

    def createChar(self, char_num, char_contents):
        """Stores a character in the LCD memory so that it can be used later.
        char_num has to be between 0 and 7 (including)
        char_contents is a list of 8 bytes (only 5 LSBs are used)"""
        if type(char_num) != int or not char_num in range(8):
            raise ValueError("Invalid char_num!")
        self.write_byte(self.LCD_SETCGRAMADDR | (char_num << 3))
        try:
            for i in range(8):
                self.write_byte(char_contents[i], char_mode=True)
        except IndexError:
            raise ValueError("Invalid char_contents!")
        finally:
            self.setCursor(0, 0)

    def noDisplay(self):
        """ Turn the display off (quickly) """
        self.displaycontrol &= ~self.LCD_DISPLAYON
        self.write_byte(self.LCD_DISPLAYCONTROL | self.displaycontrol)

    def display(self):
        """ Turn the display on (quickly) """
        self.displaycontrol |= self.LCD_DISPLAYON
        self.write_byte(self.LCD_DISPLAYCONTROL | self.displaycontrol)

    def noCursor(self):
        """ Turns the underline cursor off """
        self.displaycontrol &= ~self.LCD_CURSORON
        self.write_byte(self.LCD_DISPLAYCONTROL | self.displaycontrol)

    def cursor(self):
        """ Turns the underline cursor on """
        self.displaycontrol |= self.LCD_CURSORON
        self.write_byte(self.LCD_DISPLAYCONTROL | self.displaycontrol)

    def noBlink(self):
        """ Turn the blinking cursor off """
        self.displaycontrol &= ~self.LCD_BLINKON
        self.write_byte(self.LCD_DISPLAYCONTROL | self.displaycontrol)

    def blink(self):
        """ Turn the blinking cursor on """
        self.displaycontrol |= self.LCD_BLINKON
        self.write_byte(self.LCD_DISPLAYCONTROL | self.displaycontrol)

    def scrollDisplayLeft(self):
        """ These commands scroll the display without changing the RAM """
        self.write_byte(self.LCD_CURSORSHIFT | self.LCD_DISPLAYMOVE | self.LCD_MOVELEFT)

    def scrollDisplayRight(self):
        """ These commands scroll the display without changing the RAM """
        self.write_byte(self.LCD_CURSORSHIFT | self.LCD_DISPLAYMOVE | self.LCD_MOVERIGHT)

    def leftToRight(self):
        """ This is for text that flows Left to Right """
        self.displaymode |= self.LCD_ENTRYLEFT
        self.write_byte(self.LCD_ENTRYMODESET | self.displaymode)

    def rightToLeft(self):
        """ This is for text that flows Right to Left """
        self.displaymode &= ~self.LCD_ENTRYLEFT
        self.write_byte(self.LCD_ENTRYMODESET | self.displaymode)

    def autoscroll(self):
        """ This will 'right justify' text from the cursor """
        self.displaymode |= self.LCD_ENTRYSHIFTINCREMENT
        self.write_byte(self.LCD_ENTRYMODESET | self.displaymode)

    def noAutoscroll(self):
        """ This will 'left justify' text from the cursor """
        self.displaymode &= ~self.LCD_ENTRYSHIFTINCREMENT
        self.write_byte(self.LCD_ENTRYMODESET | self.displaymode)
