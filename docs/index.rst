Welcome to ZPUI documentation!
=================================

ZPUI (ZeroPhone UI, pronounced *zippy ui*) is a powerful user interface and app framework for small screens. It was designed for the ZeroPhone project,
but it's usable on a wide variety of single-board computers.

Minimum requirements:
    - monochrome 128x64 or larger screen (OLED/LCD)
    - 5 buttons

ZPUI is based on pyLCI, a general-purpose UI for embedded devices, an interface that supports 16x2 and larger character displays.
Currently. ZPUI is tailored for the ZeroPhone hardware, namely, the 1.3" monochrome 128x64 OLED 
and 30-key numpad (though it still retains input&output drivers from pyLCI), and it also ships with ZeroPhone-specific applications.

At the moment, ZPUI is being made more generic and tested across many different single-board computers, and the documentatin is being improved
along with the effort.

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
