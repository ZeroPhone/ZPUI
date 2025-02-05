Welcome to ZPUI documentation!
=================================

ZPUI stands for ZeroPhone UI, it's the official user interface for ZeroPhone (installed on ZeroPhone official SD card images). It allows you to interact with your ZeroPhone, using the 1.3" OLED and the 30-button numpad.

ZPUI is based on pyLCI, a general-purpose UI for embedded devices. However, unlike pyLCI, 
ZPUI is tailored for the ZeroPhone hardware, namely, the 1.3" monochrome OLED 
and 30-key numpad (though it still retains input&output drivers from pyLCI), and 
it also ships with ZeroPhone-specific applications.

Guides:
=======

* :doc:`Installing and updating ZPUI <setup>`
* :ref:`Installing ZPUI emulator <emulator>`
* :doc:`App development - how to ... ? <howto>`
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


:doc:`Development plans <plans>`

:doc:`Contact us <contact>`

:doc:`Working on documentation <docs_development>`


.. toctree::
   :maxdepth: 1
   :hidden:

   setup.rst
   config.rst
   crash_course.rst
   howto.rst
   ui.rst
   helpers.rst
   keymap.rst
   hacking_ui.rst
   logging.rst
   app_mgmt.rst
   docs_development.rst
   contact.rst
