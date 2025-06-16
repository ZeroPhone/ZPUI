.. _ui_path_picker:

#####################
PathPicker UI element
#####################

This is an UI element that allows the app's user to navigate the local filesystem
and pick files or directories.

Picking a file:

.. code-block:: python

    from zpui_lib.ui import PathPicker
    ... 
    # If initial_path is a directory, PathPicker will start in that directory
    # If initial_path is a file, PathPicker will start in its base directory and move to that file
    path = PathPicker(initial_path, i, o, name="My app's PathPicker for picking a file").activate()
    if path: # User might exit PathPicker at any time and it will return None
        purge_file_from_existence(path) # Do something with that file

Picking a directory, i.e. to read files from or to store files in:

.. code-block:: python

    from zpui_lib.ui import PathPicker
    ... 
    path = PathPicker(initial_path, i, o, dirs_only=True, name="My app's PathPicker for picking a directory").activate()
    if path:
        purge_dir_from_existence(path)

.. currentmodule:: ui

.. autoclass:: PathPicker
    :show-inheritance:
    :members: __init__,activate,deactivate,set_path,move_to_file
