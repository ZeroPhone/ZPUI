###############
Input subsystem
###############

These are the devices that receive key commands from some external source and 
route them to your applications. At the input system core, there's 
``InputListener``. It receives key events from drivers you use and routes them to 
currently active application.

Some of the available input drivers
(non-exhaustive, look in ZPUI ``input/drivers/`` directory to see more):

   * :ref:`input_hid`
   * :ref:`input_pcf8574`
   * :ref:`input_pi_gpio`

==========
InputProxy
==========

The ``i`` variable you have supplied by ``app.py`` or ``main.py`` ``load_app()`` 
in your applications is an ``InputProxy`` instance. It's operating on key names, 
such as "KEY_ENTER" or "KEY_UP". You can assign callback once a keypress with a 
matching keyname is received, which is as simple as ``i.set_callback(key_name, callback)``. 
You can also set a dictionary of ``"keyname":callback_function`` 
mappings, this would be called a **keymap**. The ``InputProxy`` only receives events
when your app is in foreground.

.. automodule:: input.input
 
.. autoclass:: InputProxy
    :members:
    :special-members:

Example usage - it should rarely be necessary for you to set callbacks directly, as this
is mostly taken care of by the UI elements.

.. code-block:: python
   
   i.stop_listen()
   i.clear_keymap() #Useful because there might be callbacks left from whatever your function was called by
   #... Set your callbacks
   i.set_callback("KEY_ENTER", my_function)
   i.listen()

========
Drivers:
========

These are only some of the drivers:

.. toctree::
   :maxdepth: 2

   input/hid.rst
   input/pcf8574.rst
   input/pi_gpio.rst
