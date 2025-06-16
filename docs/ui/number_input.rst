.. _ui_number_input:

#########################
Numeric input UI elements
#########################

.. code-block:: python
                      
    from zpui_lib.ui import IntegerAdjustInput
    start_from = 0
    number = IntegerAdjustInput(start_from, i, o).activate()
    if number is None: #Input cancelled
        return
    #process the number

.. currentmodule:: ui

.. autoclass:: IntegerAdjustInput
    :members: __init__,activate,deactivate,print_number,print_name
