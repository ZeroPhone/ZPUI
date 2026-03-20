################
Output subsystem
################

Currently ZPUI uses HD44780-compatible screens as output devices. Minimum screen size is 128x64, with 320x240 and 400x240 screens tested and working.

=============
Screen object
=============

The ``o`` variable you have supplied by ``main.py`` ``load_app()`` in your 
applications is an ``OutputProxy`` instance. It provides you with a set of functions 
available to graphical displays, and some fallback functions for character displays.

.. automodule:: output.output
.. autoclass:: OutputProxy
    :members: display_image,display_data,clear

========
Drivers:
========

.. toctree::
   :maxdepth: 2

