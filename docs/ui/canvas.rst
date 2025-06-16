.. _ui_canvas:

#####################
Canvas
#####################

.. code-block:: python
                      
    from zpui_lib.ui import Canvas
    ...
    c = Canvas(o)
    c.text("Hello world", (10, 20))
    c.display()

.. currentmodule:: zpui_lib.ui

.. autoclass:: Canvas
    :show-inheritance:
    :members: point,line,text,centered_text,vertical_text,custom_shape_text,rectangle,circle,ellipse,polygon,display,clear,get_image,get_center,invert,invert_rect,width,height,size,image,background_color,default_color,get_text_bounds,get_centered_text_bounds,check_coordinates,check_coordinate_pairs,load_font

.. autoclass:: MockOutput
