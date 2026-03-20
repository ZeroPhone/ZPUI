##############
Hardware guide
##############

.. rubric:: Absolute necessities:

* A HD44780-compatible character display, from 16x2 to 20x4. They are cheap and available in most electronics shops in the world, as well as in most starter kits.
* At least 5 simple pushbuttons (very cheap and salvageable from just about anything), or a USB keyboard/numpad.

Some remarks:

* There are Raspberry Pi shields which have a character LCDs and some buttons. They're good, too - as long as they're in the "supported" list.

  Supported shields:
    * PiFaceCAD Raspberry Pi shield
    * Adafruit 16x2 Character LCD + Keypad for Raspberry Pi
    * Chinese "LCD RGB KEYPAD ForRPI" shield (black PCB, pin-to-pin copy of aforementioned Adafruit shield)

.. rubric :: Ways to connect your hardware:

* Is it a shield ZPUI supports? Great, plug it on top of your Raspberry Pi and you're done!
* If all you have is the character display and some buttons, you can:

  * Connect them over GPIO (works for both screen and buttons) (only Raspberry Pi GPIO supported at the moment)
  * Connect them over I2C using a PCF8574 expander (works for both screen and buttons, 1$ on eBay)

* When assembling the hardware yourself, you can easily combine connection methods - for example, connect your LCD over I2C and buttons over GPIO, or use a shield for LCD and use a USB numpad.

Afterwards, follow to the :doc:`ZPUI setup <setup>` part.

Buying/choosing guide
=====================

* Want something cheap and minimum effort? Get a "LCD RGB KEYPAD ForRPI" shield. It's 6$, you can find it on eBay just by searching "Raspberry Pi LCD shield" and sorting the list by "Lowest price first". It'll take its time to arrive, but it's a great value for the price.
* Want something quickly and minimum effort? Get a PiFaceCAD shield, or an Adafruit one. They're sold by distributors in UK/USA, and will arrive quickly. Moreover, they're nicely made.
* Want something quickly and cheaply? You can assemble your own hardware from what you have. I2C expanders come in handy when you need to save pins, but connecting things through GPIO is a good alternative.
