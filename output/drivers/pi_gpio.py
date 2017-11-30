#!/usr/bin/python

#
# based on code from Adafruit, lrvick and LiquidCrystal
# lrvic - https://github.com/lrvick/raspi-hd44780/blob/master/hd44780.py
# LiquidCrystal - https://github.com/arduino/Arduino/blob/master/libraries/LiquidCrystal/LiquidCrystal.cpp
# Adafruit - https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code
#

from time import sleep

from output.output import OutputDevice


def delayMicroseconds(microseconds):
    seconds = microseconds / float(1000000)  # divide microseconds by 1 million for seconds
    sleep(seconds)

try:
    import RPi.GPIO as GPIO
except:
    print("Couldn't mock that one for ReadTheDocs")
    print("Or maybe it's a user who just doesn't have that installed?")

from hd44780 import HD44780

class Screen(HD44780, OutputDevice):
    """Driver for using HD44780 displays connected to Raspberry Pi GPIO. Presumes the R/W line is tied to ground. Also, doesn't yet control backlight. """

    def __init__(self, pins = [], rs_pin = None, en_pin = None, debug = False, **kwargs):
        """ Initializes the GPIO-driven HD44780 display

        All GPIOs passed as arguments will be used with BCM mapping.        

        Kwargs:
           * ``pins``: list of GPIO pins for driving display data bits in format [DB4, DB5, DB6, DB7]
           * ``en_pin``: EN pin GPIO number. Please, make sure it's pulled down to GND (10K is OK). Otherwise, block might start filling up the screen unexpectedly.
           * ``rs_pin``: RS pin GPIO number,
           * ``debug``: enables printing out LCD commands.
           * ``**kwargs``: all the other arguments, get passed further to HD44780 constructor

        """
        self.debug = debug
        self.rs_pin = rs_pin
        self.en_pin = en_pin
        self.pins = pins
        GPIO.setmode(GPIO.BCM)
        if not self.debug:
            GPIO.setwarnings(False)
        GPIO.setup(self.en_pin, GPIO.OUT)
        GPIO.setup(self.rs_pin, GPIO.OUT)
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
        HD44780.__init__(self, debug = self.debug, **kwargs)
        
    def write_byte(self, byte, char_mode=False):
        """Takes a byte and sends the high nibble, then the low nibble (as per HD44780 doc). Passes ``char_mode`` to ``self.write4bits``."""
        if self.debug and not char_mode:        
            print(hex(byte))                    
        self.write4bits(byte >> 4, char_mode)   
        self.write4bits(byte & 0x0F, char_mode) 

    def write4bits(self, bits, char_mode=False):
        """Writes a nibble to the display. If ``char_mode`` is set, holds the RS line high."""
        bits = bin(bits)[2:][-4:].zfill(4)
        GPIO.output(self.rs_pin, char_mode)
        for index, bit in enumerate(bits[::-1]):
            GPIO.output(self.pins[index], int(bit))
        GPIO.output(self.en_pin, False)
        delayMicroseconds(1)       # 1 microsecond pause - enable pulse must be > 450ns
        GPIO.output(self.en_pin, True)
        delayMicroseconds(1)       # 1 microsecond pause - enable pulse must be > 450ns
        GPIO.output(self.en_pin, False)
        delayMicroseconds(1)       # commands need > 37us to settle


if __name__ == "__main__":
    screen = Screen(pins=[25, 24, 23, 18], rs_pin = 22, en_pin=27)
    line = "0123456789012345"
    if True:
        screen.display_data(line, line[::-1])
        sleep(1)
        screen.display_data(line[::-1], line)
        sleep(1)
        screen.clear()
