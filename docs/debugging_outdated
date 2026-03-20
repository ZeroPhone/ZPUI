#########################
Debugging issues
#########################

====================
Debugging in general
====================

.. rubric:: Basic debugging steps:

* Launch system manually and see the error messages. Go to the directory you installed ZPUI from and launch ``python main.py``. Alternatively, use ``journalctl -u zpui.service`` for a system that was running in daemon mode but crashed unexpectedly.
* Check your connections.

.. rubric:: Hardware/driver issues:

* Check that the I2C/SPI/GPIO interfaces you're trying to use are available in ``/dev/``. You might need to run ``sudo raspi-config`` and enable the interfaces you need (for Raspberry Pi boards) or do other system-specific changes (for other boards, see the manuals the manufacturer should provide).
* In case of I2C connection, check your I2C device connection with i2cdetect, you should see its address in i2cdetect's output when connected the right way.
* Check your connections in case you assembled things manually. In case of shields, there shouldn't be any problems.


=============
Output issues
=============

.. rubric:: Basic debugging steps:

* Launch the output driver manually to display the test sequence. Go to the directory you installed ZPUI from and launch the output driver directly like ``python output/drivers/your_driver.py``. You might need to adjust variables in ``if __name__ == "__main__":`` section.
* Is the driver you're using even the correct one? See the config.json and documentation for the driver you're using. 

----------


Currently, ZPUI uses HD44780-compatible screens as output devices. Minimum screen size is 16x2. There are some known issues when using those. Again, you're not likely to run into hardware problems when using shields.

.. rubric:: Screen displaying garbage

* If using a breakout board, check if it's compatible with the driver. Some breakouts might use same ICs but have different pinouts, and any two pins interchanged can cause problems.
* Try and tie D0-D3 lines to GND. Those lines floating freely may cause instabilities, though it doesn't happen often. 
* You can try to tie the R/W line to GND, too. It's even necessary in some cases, like Pi GPIO driver. 
* Put a ~100pF capacitor between GND and EN. If screen starts quickly filling up with blocks after some time, pull the EN line down with a 10K resistor.

.. rubric:: Screen characters being shifted incorrectly

* Try to set ``"autoscroll":True`` in ``config.json`` in output description (in ``kwargs`` section).

.. rubric:: Only half of the screen is used

* Make sure you didn't set ``"autoscroll":True`` in ``config.json`` in output description (in ``kwargs`` section).

.. rubric:: Nothing on the screen

* Is first row of blocks shown? If not, regulate the contrast with a potentiometer. You can also try to tie the contrast pin to GND.
* Does screen receive 5V (not 3.3V) as VCC? Unless it's a screen that's capable of doing 3.3V (must be stated in screen's description), that's a no-go.
