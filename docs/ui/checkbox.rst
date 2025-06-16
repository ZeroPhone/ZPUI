.. _ui_checkbox:

#####################
Checkbox UI element
#####################

.. code-block:: python
                      
    from zpui_lib.ui import Checkbox
    contents = [
    ["Apples", 'apples'], #"Apples" will not be checked on activation
    ["Oranges", 'oranges', True], #"Oranges" will be checked on activation
    ["Bananas", 'bananas']]
    selected_fruits = Checkbox(checkbox_contents, i, o).activate()

.. currentmodule:: zpui_lib.ui
 
.. autoclass:: Checkbox
    :members: __init__,activate,deactivate,set_contents,print_name,print_contents
