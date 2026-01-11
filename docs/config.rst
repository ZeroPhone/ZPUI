.. _config:

ZPUI configuration files
========================

ZPUI ``config.yaml``
++++++++++++++++++++++++

.. important::

  If you're on one of the default devices (Beepy/Blepis/Colorberry/ZPUI businesscard/etc.)
  or you're using an SD card image that comes with ZPUI, you don't necessarily have to edit the config file.
  The ``config.py`` script sets a default config file for your device already.
  Feel free to skip to the "Useful examples" section!

ZPUI depends on a ``config.yaml`` file to initialize the input and output devices. 
If you're using an emulator, it expects a ``config.yaml`` in the local folder.
On non-emulator (real hardware) devices, it expects a YAML-formatted file, looking in one of the following paths
(sorted by order in which ZPUI attempts to load them):

* ``/boot/zpui_config.yaml``
* ``/boot/pylci_config.yaml``
* ``{ZPUI directory}/config.yaml``
* ``{ZPUI directory}/config.example.yaml`` (a fallback file that you shouldn't edit manually)

.. note::

  The ``config.yaml`` tells ZPUI which output and input hardware it needs to use, so
  invalid configuration might lock you out of the system. As such, if you're not using
  the emulator, it might be better to copy the file into ``/boot/zpui_config.yaml``
  and make your changes there - if you screw up and lock yourself out of ZPUI,
  it's easier to revert the changes, since you can do it by just plugging your microSD
  card in another computer and editing the file. You can also delete (or rename) the
  file to make ZPUI fallback to the config file in the ZPUI directory.

.. note::

  Also, scroll down to learn how to verify your config file after you've made changes!

ZPUI config format
-------------------

Here's how an average ZPUI config file will look like:

.. code:: yaml

   device: DEVICE_NAME (for instance, emulator, beepy or blepis)
   ui_color: "#00cafe" # can also use simple color names like "green"

Here's a config file, with a few extra input devices added:

.. code:: yaml

   device: DEVICE_NAME (for instance, emulator, beepy or blepis)
   input:
     - blepis_lora_hat # extra input device, default settings
     - driver: hid
       name: HID 04d9:1603

Here's a config where output and input drivers are defined manually:

.. code:: yaml

   output: sh1106
   input:
     - driver: hid
       name: HID 04d9:1603

Documentation for :doc:`input <input>` and :doc:`output <output>` drivers might have
sample ``config.yaml`` sections for each driver (WIP).

.. _verify_yaml:

Verifying your changes
----------------------

You can use the ``verify_config.py`` to verify that you didn't make any YAML formatting mistakes:

    ``./verify_config.py /boot/zpui_config.yaml``

If the file is correct, it'll print its contents and show how it got parsed.
If there's anything wrong with the YAML formatting or ZPUI can't interpret the file,
it will print an error message.

.. code:: bash

    arya@lappy:~/ZPUI$ ./verify_config.py config.yaml
    `config.yaml` contents:
    device: emulator
    input:
      - blepis_lora_hat
      - driver: hid
        name: HID 04d9:1603

    Parsed config for emulator:
      {'device': 'emulator', 'input': ['blepis_lora_hat', {'driver': 'hid', 'name': 'HID 04d9:1603'}]}
    Input device config:
      ['pygame_input', 'blepis_lora_hat', {'driver': 'hid', 'name': 'HID 04d9:1603'}]
    Output device config:
      pygame_emulator

If you're editing the ``config.yaml`` file externally, you might not have access to the
command-line. In that case, you can run the ``verify_config.py`` script on any computer,
you don't need to install ZPUI - simply download its files, then run the Python script in a terminal.

Useful examples
+++++++++++++++

Emulator settings
-----------------

By default, the emulator uses screen mode '1' (monochrome) and 128x64 resolution.
You can pass resolution, mode, and scale settings to the emulator by editing ``config.yaml``:

.. code-block:: yaml

    device: emulator
    resolution: 400x240
    mode: RGB
    scale: 3

Coloring your ZPUI
------------------

You can set the default ZPUI color by adding a ``ui-color`` parameter:

.. code:: yaml

   device: DEVICE_NAME (for instance, emulator, beepy or blepis)
   ui_color: "#00cafe" # can also use simple color names like "green"

Loading apps by path
--------------------

Sometimes you want to add an external app, without using the default (entrypoints-based) external app
loading mechanism. No worries - you can also load apps by giving paths to their app.py file:

.. code:: yaml

  device: beepy
  ...
  app_manager:
    app_paths:
      - path: /home/USERNAME/zpui-verycoolapp/src/zpui_verycoolapp/app.py
      - path: /home/USERNAME/zpui-verycoolapp2/src/zpui_verycoolapp2/app.py
        name: zpui_anotherverycoolapp



Blacklisting the phone app to get access to UART console
--------------------------------------------------------

You might find yourself with a cracked screen one day, and needing to connect to your
ZeroPhone nevertheless. In the unfortunate case you can't connect it to a wireless network
in order to SSH into it (as the interface is inaccessible with a cracked screen), you
can use a USB-UART to get to a console accessible on the UART port. 

Unfortunately, console on the UART is disabled by default - because UART is also used
for the GSM modem. However, you can tell ZPUI to not disable UART by disabling the phone
app, and thus enabling the USB-UART debugging. To do that, you need to:

1. Power down your ZeroPhone - since you can't access the UI, you have no other choice but
   to shutdown it unsafely by unplugging the battery.
2. Unplug the MicroSD card and plug it into another computer - both Windows and Linux will work
3. On the first partition (the boot partition), locate the ``zpui_config.yaml`` file
4. In that file, add an ``"app_manager"`` section, as shown below:

.. code:: yaml

  device: beepy
  ...  
  app_manager:
    do_not_load:
      apps/phone

Now, boot your phone with this config and you should be able to log in over UART!

.. note:: Since you're editing the ``config.yaml`` file externally, you should
          make sure it's valid YAML - :ref:`here's a guide for that. <verify_yaml>`

App-specific configuration files
++++++++++++++++++++++++++++++++

.. admonition:: TODO
   :class: warning

   This section is not yet ready. Sorry for that!

