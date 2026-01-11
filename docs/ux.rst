#############
UX guidelines
#############

==================
General guidelines
==================

Developing an app for ZPUI? Hacking on ZPUI code? Here's a few things you should keep in mind.

* You are guaranteed five buttons - up/down/left/right/enter. You might get a whole QWERTY keyboard to work with, but it's not guaranteed.

    If you write code that requires buttons other than the required five, first check if you have them available.
    You can look into ``i.available_keys`` to see which drivers can emit which keys - it'll either be a list of keys, or `'*'` for "any keys can be received".

* The five buttons have pre-defined meanings.

    * ``"KEY_LEFT"`` is expected to exit the app, UI element, view, cancel an action, etc.
    * ``"KEY_ENTER"`` is expected to confirm or redo an action, select a menu entry, etc.
    * ``"KEY_UP"/"KEY_DOWN"`` are used for up/down navigation, increment/decrement, etc.
    * ``"KEY_RIGHT"`` is used for context menus.

* Want to demonstrate a bug, an app, or a new feature? When in doubt, make a video!

    Use the Screenshot app inside ZPUI to record a video, then use the ``make_video.py`` script
    in ``screenshots/`` folder to compile a video out of a `.log` recording session file.
    The ``.log`` filename for your recording will be printed in ZPUI logs.

.. code-block:: bash

  python3 make_video.py recording-260110-033400.log

* When working on ZPUI core and the ``zpui_lib`` library, remember that ZPUI is the only system interface for some users.

    If a change touches the core or the UI library - run the tests, try out your changes live,
    and make sure the update mechanism still functions. When replacing or removing code in ZPUI,
    consider that it might be in use by other users.

* Where possible, expose internal exceptions/errors to the user

    If your code relies on running shell commands or external library, and one of them fails
    in a weird way or outputs something entirely unexpected for you,
    consider putting the exception/output into a ``TextReader`` and showing it to the user,
    so that the user has a chance at identifying or resolving the problem.
    A good reference for this is the recently added Tailscale app.

* Make use of app template helper scripts

    The example app template (``zpui-example-app``) has plenty of scripts to help you.
    For instance, the ``rename.py`` script is crucial to run to give your app a name
    before you install your app, so that ZPUI internal app tracking doesn't break.
    Watch out for other scripts in the template folder, too -
    for instance, the ``check_release.py`` script will check that you've cleaned out README.md
    and other files from template-specific helper text before distributing the app.
    The ``install.py`` script is also a good place for your own code you'd like to be ran
    on app install.

* Use human-readable config files where possible

    Your app will likely have some user-configurable parameters. It's better
    if you use human-friendlier formats like YAML instead of JSON or custom formats,
    so that users get a chance at tweaking the app themselves.

===================================
When going beyond stock UI elements
===================================

Drawing your app UI using ``Canvas``?

* When not using ZPUI-provided UI code, cache heavy UI operations to speed up your code a lot.

    Cache results of canvas drawing, image rendering, and similar computing-intensive operations.
    This will speed up your UIs significantly - up to orders of magnitude in improvements.
    A good reference for this is the ``BebbleGridView`` in ``zpui_lib``'s ``ui/grid_menu.py``,
    which is the main menu for Beepy/Blepis/Colorberry and default menu for screen sizes above 240x240 -
    caching the rendered tiles into memory and only pasting on refresh has sped up menu scrolling by about 20 times.

* There are a few common screen sizes that'll be used with ZPUI. 

    Specifically, these are 128x64, 320x240, and 400x240. Try and check that your app works on all of those,
    or add a ``can_load()`` statement to your app so that the app doesn't load on smaller screens.
    For a move from 320x240 to 400x240, it's entirely acceptable to add background-colored borders
    on the sides.

===========================================
When developing for Beepy/Blepis/Colorberry
===========================================

* When requiring fine-grained movements, duplicate the touchpad movements onto keyboard keys

    The Q20 keyboard touchpad can sometimes emit duplicate events, and it has some lag going for it, too.
    If you're designing an app that requires more granular movements (i.e. a game), consider
    also processing E/S/D/X/F keys on the QWERTY keyboard as your LEFT/UP/ENTER/DOWN/RIGHT keys.
    These specific keys are picked because the D key has a "pimple" on the Q20 keyboard,
    so it's easier to find with a finger as a "center" key.
