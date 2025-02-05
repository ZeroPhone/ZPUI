.. _app_mgmt:
                    
####################################
Managing and developing applications
####################################

General information
===================

* Applications are simply folders which are made importable by Python by adding an ``__init__.py`` file. ZPUI loads ``main.py`` file residing in that folder.
* You can combine UI elements in many different ways, including making nested menus, which makes apps less cluttered. 
* ZPUI main menu can have submenus. Submenu is just a folder which has ``__init__.py`` file in it, but doesn't have a ``main.py`` file. It can store both application folders and child submenu folders.

  * To set a main menu name for your submenu, you need to add ``_menu_name = "Pretty name"`` in ``__init__.py`` file of a submenu.
  * Submenus can be nested - just create another folder inside a submenu folder. However, submenu inside an application folder won't be detected.

* All application modules are loading when ZPUI loads. When choosing an application in the main menu/submenu, its global ``callback`` or ``ZeroApp.on_load()`` is called. It's usually set as the ``activate()`` method of application's main UI element, such as a menu.
* You can prevent any application from autoloading (but still have an option to load it manually) by placing a ``do_not_load`` file (with any contents) in application's folder (for example, see skeleton application folder).

Getting Started
===============
ZPUI enables two way of developping apps. One is function-based, the other one is class-based.

Function-based
--------------
Function-based apps need two functions to work : ``init_app`` and ``callback``.

* ``init_app(i, o)`` is called when the app is **loaded**. That is, when the UI boots. Avoid doing any heavy work here, it would slow down everything, and there is no guarantee the app is going to be activated at this point. You may want to keep a reference to the two parameters for later usage. See below.
* ``callback()`` is called when the app is actually opened and brought to foreground. This is where most of your code should belong.
* ``menu_name`` is a global variable that can be set to define the name of the application shown in the main menu. If not provided, it will fall back to the name of the parent directory.
* ``global i, o`` are global variables commonly used to keep a reference to the input and output devices passed in the ``init`` function.

Usage example :  :ref:`skeleton_app <skeleton_app>`

Class-based
-----------
Class-based apps need a single ``class`` inheriting from ``ZeroApp`` to work.

* ``init_app(self)`` is called when the app is **loaded**. That is, when the UI boots. Avoid doing any heavy work here, it would slow down everything, and there is no guarantee the app is going to be activated at this point. There's ways to do heavy stuff on boot, check the Example page!
* ``on_load(self)`` is called when the app is actually opened and brought to foreground. This is where most of your code should belong.
* ``menu_name`` is a member variable that can be set to define the name of the application shown in the main menu. If not provided, it will fall back to the name of the parent directory.

You can see :ref:`class skeleton app <class_skeleton_app>` for an example.

Development tips
================

* For starters, take a look at the :ref:`skeleton app <skeleton_app>` and :ref:`class skeleton app <class_skeleton_app>`
* You can launch ZPUI in a "single application mode" using ``main.py -a apps/app_folder_path``. There'll be no main menu constructed, and exiting the application exits ZPUI.
* You should not set input callbacks or output to screen while your application is not the one active. It'll cause screen contents set from another application to be overwritten, which is bad user experience. Make sure your application is the one currently active before outputting things and setting callbacks.
