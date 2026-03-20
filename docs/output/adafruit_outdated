.. _output_adafruit:

####################################################################
Adafruit CharLCD Plate&Chinese "LCD RGB KEYPAD" shield output driver
####################################################################

This driver works with Adafruit Raspberry Pi character LCD&button shields, as well as with Chinese clones following the schematic (can be bought for 5$ on eBay, typically have "LCD RGB KEYPAD ForRPi" written on them).

If you have a genuine Adafruit board, pass ``"chinese":false`` keyword argument to the driver in config.json so that the backlight works right.

Sample ``config.json`` section for Adafruit board:

.. code:: json

    "output":
       [{
         "driver":"adafruit_plate",
         "kwargs":
         {
          "chinese":false
         }
       }]


Sample ``config.json`` section for Chinese clone:

.. code:: json

    "output":
       [{
         "driver":"adafruit_plate"
       }]


.. note:: Generally, you won't need to edit ``config.json`` if you're using this shield because it'll be done automatically by ``config.sh``.

.. toctree::

.. automodule:: output.drivers.adafruit_plate
 
.. autoclass:: Screen
    :members:
    :special-members:
