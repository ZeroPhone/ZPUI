.. _ui_canvas:

#####################
Canvas
#####################

.. code-block:: python
                      
    from zpui_lib.ui import Canvas
    ...
    c = Canvas(o)
    c.centered_text("Hello world", font=("Fixedsys62.ttf", 16))
    c.display()

.. currentmodule:: zpui_lib.ui

.. autoclass:: Canvas
    :members:
    :exclude-members: default_font

.. autoclass:: MockOutput
    :members:

.. autofunction:: open_image
.. autofunction:: invert_image
.. autofunction:: crop
.. autofunction:: expand_coords
.. autofunction:: replace_color
.. autofunction:: swap_colors
