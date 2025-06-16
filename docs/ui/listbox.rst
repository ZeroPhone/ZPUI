.. _ui_listbox:

#####################
Listbox UI element
#####################

.. code-block:: python
                      
    from zpui_lib.ui import Listbox
    ... 
    lbc = [
    ["Option1", "option_1"],
    ["option_2"], # will be used as both name and value
    ]
    choice = Listbox(lbc, i, o, name="My listbox of my app").activate()
    if choice: # user didn't cancel and selected something
        # do things

``Listbox`` will return the selected option's value (``element[1]``), or name
(``element[0]``) if no value was passed. Otherwise, if the user exited ``Listbox``
by pressing LEFT, returns ``None``.

.. currentmodule:: zpui_lib.ui
 
.. autoclass:: Listbox
    :show-inheritance:
    :members: __init__,activate,deactivate,set_contents
