.. _ui_menu:

#####################
Menu UI element
#####################

.. code-block:: python
                      
    from zpui_lib.ui import Menu
    ... 
    menu_contents = [
      ["Do this", do_this],
      ["Do this with 20", lambda: do_this(x=20)],
      ["Do nothing"],
      ["Do this with 30; right click for 40", lambda: do_this(x=30), lambda: do_this(x=40)],
      ["My submenu", submenu.activate]
    ]
    Menu(menu_contents, i, o, "My menu").activate()

For ``Menu`` usage examples, tips, and tricks, see :ref:`tutorial 1 <tutorial_1>` and :ref:`tutorial 2 <tutorial_2>`!

``Menu`` always returns ``None``, so you don't need to check its return value.

.. currentmodule:: zpui_lib.ui

Instantiating the ``Menu``:

.. autoclass:: Menu
    :members: __init__,activate,deactivate,set_contents

More info:

.. autoclass:: Menu
    :show-inheritance:
    :inherited-members:
    :members:
    :member-order: groupwise
    :noindex:

.. autoexception:: MenuExitException
    :show-inheritance:

