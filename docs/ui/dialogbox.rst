.. _ui_dialogbox:

#####################
DialogBox UI element
#####################

This UI element allows you to make sure the user actually wants to proceed with
some kind of action/decision.

.. code-block:: python
                      
    from zpui_lib.ui import DialogBox
    ... 
    choice = DialogBox("ync", i, o, name="My dialogbox of my app").activate()
    if choice: "Yes" was selected
        # do things

By default, you can pass string values like "ync" (or "yn", or "yc", or "cy"), where
the "y", "n" and "c" characters will be parsed as "Yes" (``True``), "No" (``False``)
and "Cancel" (``None``) options respectively (``True``, ``False`` and ``None`` being
return values). Exiting by using LEFT will also result in ``None`` being returned.

You can also pass custom labels/return values like this:

.. code-block:: python
                      
    choice = DialogBox([["Abort", "abort"], ["Retry", "retry"], ["Ignore", "ignore"]], i, o, name="My dialogbox of my app").activate()

.. currentmodule:: zpui_lib.ui

.. autoclass:: DialogBox
    :show-inheritance:
    :members: __init__,activate,deactivate,set_start_option
