.. _config:

ZPUI configuration files
========================

ZPUI ``config.json``
++++++++++++++++++++++++

.. warning::

  TODO A migration to YAML has happened, and this entire section has to be overhauled

.. important::

  By default, ZeroPhone SD card images and ZPUI installs ship with config.json files
  that are suitable for usage out-of-the-box. Unless you want to tweak your IO drivers'
  initialization parameters or need to debug ZPUI in case of hardware trouble,
  you won't need to edit ZPUI configuration files.

ZPUI depends on a ``config.json`` file to initialize the input and output devices. 
To be exact, it expects a JSON-formatted file in one of the following paths (sorted by order
in which ZPUI attempts to load them):

* ``/boot/zpui_config.json``
* ``/boot/pylci_config.json``
* ``{ZPUI directory}/config.json``
* ``{ZPUI directory}/config.example.json`` (a fallback file that you shouldn't edit manually)

.. note::

  The ``config.json`` tells ZPUI which output and input hardware it needs to use, so
  invalid configuration might lock you out of the system. Thus, it's better to make changes
  in ``/boot/zpui_config.json`` - if you screw up and lock yourself out of ZPUI,
  it's easier to revert the changes since you can do it by just plugging your microSD
  card in another computer and editing the file. You can also delete (or rename) the
  file to make ZPUI fallback on a default config file.

ZPUI config format
-------------------

Here's the default ZPUI config right now:

.. include:: ../default_config.yaml
    :code: yaml

Here's the config file format: 

.. code:: json

   {
     "input":
     [{
       "driver":"driver_filename",
       "args":[ "value1", "value2", "value3"...]
     }],
   "output":
     [{
       "driver":"driver_filename",
       "kwargs":{ "key":"value", "key2":"value2"}
     }]
   }

Documentation for :doc:`input <input>` and :doc:`output <output>` drivers might have
sample ``config.json`` sections for each driver. ``"args"`` and ``"kwargs"`` get passed
directly to drivers' ``__init__`` method, so you can read the driver documentation
or source to see if there are options you could tweak.


.. _verify_json:

Verifying your changes
----------------------

You can use ``jq`` to verify that you didn't make any JSON formatting mistakes:

    ``jq '.' config.json``

If the file is correct, it'll print it back. If there's anything wrong with the JSON
formatting, it'll print an error message:

    ``pi@zerophone:~/ZPUI#$ jq '.' config.json``
    ``parse error: Expected separator between values at line 7, column 10``

You might need to install ``jq`` beforehand:

    ``sudo apt-get install jq``

If you're editing the ``config.json`` file externally, you might not have access to the
command-line. In that case, you can use an online JSON validator, such as `jsonlint.com`_
- copy-paste contents of ``config.json`` there to see if the syntax is correct.

.. _jsonlint.com: https://jsonlint.com/

App-specific configuration files
++++++++++++++++++++++++++++++++

.. admonition:: TODO
   :class: warning

   This section is not yet ready. Sorry for that!

Useful examples
+++++++++++++++

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
3. On the first partition (the boot partition), locate the ``zpui_config.json`` file
4. In that file, add an ``"app_manager"`` dictionary (a "collection" in JSON terms)
5. Add the path to the phone app to a ``"do_not_load"`` list inside of it

The resulting file should look like this, as a result:

.. code:: json

  {
   "input": ... ,
   "output": ... ,
   "app_manager": {
      "do_not_load":
         ["apps/phone"]
    }
  }

Now, boot your phone with this config and you should be able to log in over UART!

.. note:: Since you're editing the ``config.json`` file externally, you should
          make sure it's valid JSON - :ref:`here's a guide for that. <verify_json>`
