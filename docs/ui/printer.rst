.. _ui_printer:

#####################
Printer UI element
#####################

.. code-block:: python
                      
    from zpui_lib.ui import Printer
    Printer(["Line 1", "Line 2"], i, o, 3, skippable=True)
    Printer("Long lines will be autosplit", i, o, 1)

.. currentmodule:: zpui_lib.ui

.. autofunction:: Printer

.. autofunction:: PrettyPrinter

.. autofunction:: GraphicsPrinter
