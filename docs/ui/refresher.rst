.. _ui_refresher:

#####################
Refresher UI element
#####################

.. code-block:: python
                      
    from zpui_lib.ui import Refresher
    counter = 0
    def get_data():
        counter += 1
        return [str(counter), str(1000-counter)] #Return value will be sent directly to output.display_data
    Refresher(get_data, i, o, 1, name="Counter view").activate()

.. currentmodule:: zpui_lib.ui

.. autoclass:: Refresher
    :members: __init__,activate,deactivate,print_name
