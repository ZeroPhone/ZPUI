.. _helpers:

#######
Helpers
#######

These are various objects and functions that help you with general-purpose 
tasks while building your application - for example, config management, 
running initialization tasks or exiting event loops on a keypress. 
They can help you build the logic of your application quicker, and allow 
to not repeat the code that was already written for other ZPUI apps.

ProHelper
---------

:ref:`See here for ProHelper documentation and usage examples <process_helper>`

.. automodule:: helpers

local_path_gen helper
---------------------

.. autofunction:: local_path_gen

ExitHelper
----------

.. autoclass:: ExitHelper
    :members: start,do_exit,do_run,stop,reset

Usage:

.. code-block:: python

    from helpers import ExitHelper
    ...
    eh = ExitHelper(i)
    eh.start()
    while eh.do_run():
        ... #do something until the user presses KEY_LEFT

There is also a shortened usage form:

.. code-block:: python

    ...
    eh = ExitHelper(i).start()
    while eh.do_run():
        ... #do your thing

Oneshot helper
--------------

.. autoclass:: Oneshot
    :members: run,running,finished, reset

Usage:

.. code-block:: python

    from helpers import Oneshot
    ...
    def init_hardware():
        #can only be run once

    #since oneshot is only defined once, init_hardware function will only be run once,
    #unless oneshot is reset.
    oneshot = Oneshot(init_hardware)
    
    def callback():
        oneshot.run() #something that you can't or don't want to init in init_app
        ... #do whatever you want to do

BackgroundRunner helper
-----------------------

.. autoclass:: BackgroundRunner
    :members: run,running,finished,failed,reset,threaded_runner

Usage:

.. code-block:: python

    from helpers import BackgroundRunner
    ...
    def init_hardware():
        #takes a long time

    init = BackgroundRunner(init_hardware)
    
    def init_app(i, o):
        ...
        init.run() #something too long that just has to run in the background,
        #so that app is loaded quickly, but still can be initialized.

    def callback():
        if init.running: #still hasn't finished
            PrettyPrinter("Still initializing...", i, o)
            return
        elif init.failed: #finished but threw an exception
            PrettyPrinter("Hardware initialization failed!", i, o)
            return
        ... #everything initialized, can proceed safely
        
Combining BackgroundRunner and Oneshot
--------------------------------------

.. code-block:: python

    from helpers import BackgroundRunner, Oneshot
    ...
    def init_hardware():
        #takes a long time, *and* can only be run once

    init = BackgroundRunner(Oneshot(init_hardware).run)
    
    def init_app(i, o):
        #for some reason, you can't put the initialization here
        #maybe that'll lock the device and you want to make sure 
        #that other apps can use this until your app started to use it.

    def callback():
        init.run() 
        #BackgroundRunner might have already ran
        #but Oneshot inside won't run more than once
        if init.running: #still hasn't finished
            PrettyPrinter("Still initializing, please wait...", i, o)
            eh = ExitHelper(i).start()
            while eh.do_run() and init.running:
                sleep(0.1)
            if eh.do_exit(): return #User left impatiently before init has finished
            #Even if the user has left, the hardware_init will continue running
        elif init.failed: #finished but threw an exception
            PrettyPrinter("Hardware initialization failed!", i, o)
            return
        ... #everything initialized, can proceed safely
