Welcome to ZPUI documentation!
=================================

ZPUI (ZeroPhone UI, pronounced *zippy ui*) is a powerful user interface and app framework for small screens. It was designed for the ZeroPhone project,
but it's usable on a wide variety of single-board computers.

Currently stock-supported devices:

* Beepy, Colorberry
* Blepis
* ZPUI businesscard (both Pi GPIO and QWIIC)
* OG ZeroPhone

Other device support is easy enough - most of the time, you'll only need to edit a config file.

Minimum requirements:

    * monochrome/color screen larger than 128x64. For instance, one of:

        * 128x64 OLED (common)
        * 320x240 color LCD screen
        * 400x240 Sharp monochrome or JDI color screen

    * 5 buttons (up/down/left/right/enter), with support for QWERTY keyboards. For instance, one (or multiple) of:

        * Pi GPIO buttons
        * Pi GPIO matrix button
        * I2C/SPI GPIO expander-connected buttons
        * HID device (USB, I2C, emulated etc.)

ZPUI is based on pyLCI, a general-purpose UI for embedded devices, an interface that supports 16x2 and larger character displays.
Currently. ZPUI is tailored for Blepis and ZPUI businesscard hardware.

At the moment, ZPUI is being made more generic and tested across many different single-board computers,
and the documentation is being improved along with the effort.

Guides:
=======

* :doc:`Installing and updating ZPUI <setup>`
* :ref:`Installing ZPUI emulator <emulator>`
* :doc:`Developing your first app <tutorial_1>`
* :doc:`App development how-tos <howto>`
* :doc:`ZPUI configuration files <config>`
* :doc:`Hacking on UI <hacking_ui>`
* :doc:`Logging configuration <logging>`

References:
===========

- :doc:`Crash course <crash_course>`
- :doc:`UI elements <ui>`
- :doc:`Helper functions <helpers>`
- :doc:`Input system <input>`

  - :doc:`Keymaps <keymap>`

- :doc:`Output system <output>`


:doc:`Usability guidelines <ux>`

:doc:`Development plans <plans>`

:doc:`Contact us <contact>`

:doc:`Working on documentation <docs_development>`


.. toctree::
   :maxdepth: 1
   :hidden:

   setup.rst
   config.rst
   tutorial_1.rst
   crash_course.rst
   howto.rst
   ui.rst
   helpers.rst
   keymap.rst
   hacking_ui.rst
   logging.rst
   ux.rst
   app_mgmt.rst
   docs_development.rst
   contact.rst
