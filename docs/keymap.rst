.. _keymap:

#######
Keymaps
#######

.. contents::
    :local:
    :depth: 2

What's a keymap?
================

Keymap is a mapping between keys pressed by the user and functions (callbacks) that are called by the input processor. For example, if you have a currently active UI element ``el`` that, in its keymap, maps a ``KEY_LEFT`` key to its ``deactivate`` method, ``el.deactivate`` will be called by the input processor (from a separate thread) when user presses ``KEY_LEFT``.

Key names
=========

Key names are strings that start with ``"KEY_"``. They're modelled after the `Linux input keycode names`_, but might be different where developer-friendliness is concerned. For more info about ZeroPhone key names, see `this Wiki page`_. There are 5 basic keys that you can expect to be available on any platform (including ZeroPhone) - ``"KEY_DOWN"``, ``"KEY_UP"``, ``"KEY_LEFT"``, ``"KEY_RIGHT"`` and ``"KEY_ENTER"``.

If you're writing your own UI elements or apps that define their own callbacks, it's best if you can map all the main functions onto these 5 keys - though there's nothing wrong if you're making an app that's fundamentally ZeroPhone-tailored, i.e. implementing a calculator with only arrow keys would be tricky.

.. _Linux input keycode names: https://elixir.bootlin.com/linux/v2.6.38/source/include/linux/input.h#L182
.. _this Wiki page: https://wiki.zerophone.org/Keypad

Typical keymaps
===============

Keymaps, fundamentally, are dictionaries where keys are key names and values are callbacks. UI elements and apps need to take care to ensure that, when they're active, the correct keymap is set, while not interfering with other UI elements that might use the same input proxy object.

For example, imagine a (parent) menu that links to a child menu. When the parent menu calls the child menu, child menu sets its own keymap - and parent menu needs to not change the keymap until the child menu exits. Once the child menu exits, however, the parent menu needs to set its keymap again (as the input proxy's keymap was previously set to the child menu's keymap).

Thankfully, all this is taken care of when you're using stock UI elements - you only need to worry about this if you manually use the ``i.set_callback``, ``i.set_keymap`` and other functions. This is mostly described so that you have insight into how ZPUI input processing works.

Key states
==========

By default, callbacks are only called when key is pressed, as that covers the majority
of usecase and is an intuitive choice. However, you can also make your callbacks receive
key events by using a decorator:

.. code-block:: python

    from helpers import cb_needs_key_state, KEY_HELD # Also has KEY_PRESSED and KEY_RELEASED

    @cb_needs_key_state
    def up_held_cb(state):
        if state == KEY_HELD:
            print("UP key held!")
    
    i.set_callback("KEY_UP", up_held_cb)

Of course, for now, this does imply that you need to set a single callback for the same
key, even if you need to process different states.

Streaming callbacks also receive the key name:

.. code-block:: python

    from helpers import cb_needs_key_state, KEY_PRESSED, KEY_RELEASED, KEY_HELD

    @cb_needs_key_state
    def state_cb(key, state):
        state_name = {KEY_PRESSED:"down", KEY_HELD:"hold", KEY_RELEASED:"up", None:"down"}[state]
        print("{} - {}".format(key, state_name))
    
    i.set_streaming(key_state_cb)

.. note:: The function will be modified in-place. If you need the ``cb_needs_key_state``
          to return a new function instead of modifying the existing one, call it with
          ``new_function=True``.

.. warning:: Not all drivers support key state (though it will likely be a matter of time
             and requests to add it to drivers), in that case, you will get ``None``.
             Also, not all drivers support "key held" state - but the default ZP keypad
             driver and the HID driver do.

.. _keymap_for_custom_ui:

Changing UI elements' keymaps in your own apps
==============================================

Most UI elements (specifically, BaseUIElement-based-ones) allow you to add and override keymap entries, both for external and internal functions. Let's take the keymap of an IntegerAdjustElement, for instance:

.. code-block:: python

    def generate_keymap(self):
        return {
        "KEY_RIGHT":'reset',
        "KEY_UP":'increment',
        "KEY_DOWN":'decrement',
        "KEY_F3":lambda: self.increment(multiplier=10),
        "KEY_F4":lambda: self.decrement(multiplier=10),
        "KEY_ENTER":'select_number',
        "KEY_LEFT":'exit'
        }

You will notice that some elements in the keymap are strings, and some are functions. The main difference is - *the string callbacks refer to the internal methods* of the UI element itself, i.e. ``"KEY_LEFT":"deactivate"`` for an ``IntegerAdjustElement`` named ``ia`` means that, once you press ``KEY_LEFT``, ``ia.deactivate`` will be called. This allows to define keymap callbacks in a more straightforward way, both when writing an UI element and when remapping its callbacks. In addition to that, when string callbacks are used, the UI element will not go into background while processing it (so, any redraws will still happen).

In comparison, function callbacks will be 1) executed directly (with no positional/keyword arguments supplied) 2) will suspend the UI element into background during execution (so, redraws will not happen if UI element's refresh() is wrapped into ``to_be_foreground``).

How can you use this?
---------------------

First of all, when instantiating an UI element, you can replace some of the callbacks by using a ``keymap={}`` init argument, For example, if you create an ``IntegerAdjustElement`` object like this: ``IntegerAdjustElement(0, i, o, name="...", ..., keymap={"KEY_F1":your_function})``, once it's active, your_function will be called when the user presses ``KEY_F1`` (and the UI element will go into background, so you can set your own callbacks and draw on the screen all you want). This way, you can create all kinds of context menus. If there's an existing callback set on a key you want to use, it will be replaced.

Then, you can also remap internal methods of the UI element. For example, if you want to flip ``IntegerAdjustElement``'s up/down key actions, you can initialize it like this: ``IntegerAdjustElement(0, i, o, name="...", ..., keymap={"KEY_UP":"decrement", "KEY_DOWN":"increment"})``. This way, when the user presses UP, the number will decrement instead of incrementing, and vice-versa.

.. warning:: Keep in mind that ``KEY_LEFT`` is a special key, as it's the default "go back" key and UI elements are built in a way that enforces this guideline. If KEY_LEFT is present in an external keymap for UI elements like ``Refresher`` and ``Menu`` (and derivative UI elements), it will be replaced with the default ``"deactivate"`` callback. To avoid that, you should set the ``override_left`` keyword argument to ``False`` when instantiating the UI element.

Shortcuts
---------

Do you always need to use the ``keymap=`` replacements? No, there's often a better way.

  * If you need to add a "F1 and F2 buttons do something" function to an UI element, use the ``FunctionKeyOverlay`` - it will also show button labels on the screen.
  * If you need to add a "help is shown on F5" function to an UI element, use the ``HelpOverlay`` - it will also show a small "H" icon in the top left, which is something users can recognize as a "help available" marker.

Remapping keys globally
=======================

It's possible to remap keys from your input devices, i.e. if your keyboard sends ``KEY_KPENTER`` and you want the UI elements to receive ``KEY_ENTER``. For that, you will want to edit ZPUI's ``config.json`` file as follows:

.. code:: json

    {
     "input":
     [
      {
       "driver":"custom_i2c",
       "kwargs":
       {
        "name_mapping": {"KEY_KPENTER":"KEY_ENTER"}
       }
      }
     ],
    ...
    }

.. note:: Keep in mind that many drivers already have their own (override-able) replacement rules. I.e. the ``KEY_KPENTER=>KEY_ENTER`` rule is already hardcoded into the HID and pygame (emulator) drivers.

.. warning:: :doc:`Usual config.json editing rules <config>` apply - if you're changing the config file for a ZeroPhone, it's best if you edit ``/boot/zpui_config.json``, as if you make a syntax mistake, a failsafe config file will be used.
