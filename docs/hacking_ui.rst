.. _hacking_ui:

Hacking on UI
#############

If you want to change the way ZPUI looks and behaves for you, 
make a better UI for your application by using more graphics or even
design your own UI elements, these directions will help you on your way.

Using the ZPUI emulator
=======================

ZPUI has an emulator that will allow you to test your applications, UI tweaks 
and ZPUI logic changes, so that you don't have to have a ZeroPhone to develop 
and test your UI.

It will require a Linux computer with a graphical interface running (X forwarding 
might work, too) and Python 2.7 available. :ref:`Here are the setup and usage instructions <emulator>`.

Tweaking how the UI looks
=========================

ZPUI allows you to modify the way UI looks. The main way is tweaking UI element 
"views" ( a view object defines the way an UI element is displayed ). So, you can 
change the look of a certain UI element (say, main ZPUI menu), or a group of 
elements (like, force a certain view for all checkboxes). You can also define your 
own views, then apply them to UI elements using the same method. To know more about it,
`read here`_.

If your needs aren't covered by this, feel free to modify the ZPUI code - 
it strives to be straightforward, and the parts that aren't are either 
covered with comments and documentation, or will be covered upon request.
If you need assistance, contact us on IRC or email!

.. note:: If you decide to modify the ZPUI code, :doc:`here's a starting point <app_mgmt>`. Also, please `open an issue`_ on GitHub describing your changes - we can include it as a feature in the next versions of ZPUI!
.. warning:: Modifying ZPUI code directly might result in merge conflicts if you will update using ``git pull``, or the built-in "Update ZPUI" app. Again, please do consider opening an issue on GitHub proposing your changes to be included in the mainline =)

.. _read here: http://wiki.zerophone.org/index.php/Tweaking_ZeroPhone_UI
.. _open an issue: https://github.com/ZeroPhone/ZPUI/issues/new

Making and modifying UI elements
================================

If :doc:`existing UI elements <ui>` do not cover your usecase, you can also 
make your own UI elements! Use the `code for existing UI elements`_ as guidelines if you feel confident enough
or :doc:`contact us <contact>` if you need help.

Also, check if the UI element you want is mentioned in `ZPUI GH issues`_- 
there might already be progress on that front, or you might find some 
useful guidelines.

.. _code for existing UI elements: https://github.com/ZeroPhone/ZPUI/tree/master/ui
.. _ZPUI GH issues: https://github.com/ZeroPhone/ZPUI/issues

Attaching to the ZPUI instance
==============================

In case where you need to debug some hiccup or simulate some condition in the
framework itself, you can attach to the ZPUI instance and debug the framework's
behaviour. This will not allow you to debug individual apps, however,
if you need to attach to an app, you can modify its code in the same way that ZPUI
``main.py`` itself was modified.

First, you need to install ``python-rfoo`` from Debian repositories, if it's not
installed already. ZeroPhone SD card images will have it installed by default,
otherwise, here's how you do it:

    ``sudo apt install python-rfoo``

If you don't yet have it installed, it can be done any time before actually launching
the debug console. Then, find PID of the current ZPUI instance:

    ``ps ax|grep python``

You might have multiple entries, one of them will look like "python main.py",
get the PID from it. PID is the process number, which in our case is likely
going to be from 3 to 5 digits long. Once you have the PID number, signal
ZPUI to launch the console:

    ``kill -USR2 74856`` (where ``74856`` is your PID number)

Then, launch a Python interpreter and run the following commands:

.. code-block:: python

    from rfoo.utils import rconsole
    rconsole.interact(port=9377)

.. code-block:: console

    pi@zerophone-prototype:~ $ python
    Python 2.7.13 (default, Sep 26 2018, 18:42:22)
    [GCC 6.3.0 20170516] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> from rfoo.utils import rconsole
    >>> rconsole.interact(port=9377)
    Python 2.7.13 (default, Sep 26 2018, 18:42:22)
    [GCC 6.3.0 20170516] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    (ProxyConsole)
    >>>

Tab completion is supported, and don't be afraid to use ``dir()`` to	 find out more
about components.

TODO: move this into ``debugging.rst``, once ``debugging.rst`` is brought up to date.

Testing the UI
==============

There are two ways to test UI elements:

1. Running existing tests 
-------------------------

There's a small amount of tests, they're being added when bugs are found, 
sometimes also when features are added. **From** ``ui/tests`` **folder**, 
run existing tests like:

    ``python -m unittest TEST_FILENAME`` *(without .py at the end)*

For example, try:

    ``python -m unittest test_checkbox``

2. Running example applications
-------------------------------

There are `example applications`_ available for you to play with UI elements.
You can run ZPUI in single-app mode to try out any UI element before using it:

    ``python main.py -a apps/example_apps/checkbox_test``

You can also, of course, use the code from example apps as a reference
when developing your own applications.

.. _example applications: https://github.com/ZeroPhone/ZPUI/tree/master/apps/example_apps

Contributing your changes
=========================

Send us `a pull request`_! If your changes affect the UI element logic, please 
try and make a test that checks whether it really works. If you're adding a new UI
element, add docstrings to it - describing purpose, args and kwargs, as well as
an example application to go with it.

.. _a pull request: https://github.com/ZeroPhone/ZPUI/compare

Useful links
============

* `Chat logs about ZPUI/ZeroPhone`_

.. _Chat logs about ZPUI/ZeroPhone: http://wiki.zerophone.org/index.php/Chat_logs_about_ZeroPhone/ZPUI
