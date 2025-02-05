.. _process_helper:

############################################
ProHelper - external process helper tutorial
############################################

This is a tutorial on writing a small wrapper class to control an external process,
using ``ProHelper`` class available in ZPUI.

Currently, ``ProHelper`` can:

* Launch a process in background and let you do stuff, periodically checking if it's finished
* Process (or just print) output of the process as it goes on
* Pass input to the process
* Let you terminate the process at random
* Let you check exit code of the process
* Emulate a ``tty``-like terminal
* Can be subclassed, making it possible to write a wrapper class for a specific command

====================================
Example - wrapping around ``passwd``
====================================

For ZeroPhone, we need a wrapper around ``passwd`` - a command-line utility

Conditions:

* We need to change a password for the "pi" user to a specific string
* No need to pass the current password (for now, ZPUI runs as root)

Workflow:

* Launching ``passwd`` through ``ProHelper``
* Reading its output to know when ``passwd`` is ready to accept the code
* Entering the password
* Repeating the password when ``passwd`` needs it

As ``passwd`` is going to be an external process, we will want to make a way to determine
its state from the Python code that will be overseeing it.

Starting experiments
--------------------

Go to a ZPUI install :ref:`(preferrably, the local install) <local_system_copy>` and
cd into the `helpers/` directory. Then, run `python -i process.py play`:

.. code-block:: console

    cd /home/pi/ZPUI/helpers
    python -i process.py play

Create a new instance of ProHelper that'd run ``passwd pi``, with the default of printing
all the output out as it comes. Launch it using ``.run()``, then poll the process to see
the output:

.. code-block:: python

    >>> pwdhelper = ProHelper(["passwd", "pi"], output_callback="print")
    >>> pwdhelper.run()
    >>> pwdhelper.poll()
    Enter new UNIX password: >>>

Now, we can send input to it:

.. code-block:: python

    >>> pwdhelper.write("new_password\n")
    13 # Length of the input sent to the process

If the process expects "Enter" to be pressed after input, don't forget to send '\n' at the end.

Let's poll the ``passwd`` process and see if there's any new input. We can also check whether the process is still ongoing!

.. code-block:: python

    >>> pwdhelper.poll()
    
    Retype new UNIX password: >>>
    >>>  pwdhelper.is_ongoing()
    True

We got new output, which was printed out (as the default 'print' callback does). Now,
let's send the password again, poll the process and check if it's finished:

.. code-block:: python

    >>> pwdhelper.write("new_password\n")
    13
    >>> pwdhelper.poll()
    
    passwd: password updated successfully
    >>> pwdhelper.is_ongoing()
    False

We can get the return code:

.. code-block:: python

    >>> pwdhelper.get_return_code()
    0

Writing a ``passwd`` function
-----------------------------

Let's make a small wrapper-like function that uses ``ProHelper``, takes ``user`` and
``password`` arguments and returns something useful (whether the password change was
successful).

Quick&dirty way
+++++++++++++++

What's the simplest (and dirtiest) way to make such a function?

.. code-block:: python

    # DO NOT COPY-PASTE - this is QUICK&DIRTY
    def passwd(username, password):
        status = ["unknown"] # hack, explained below
        ph = ProHelper(["passwd", username], output_callback=None)
        ph.run()
        p.write(password+'\n')
        p.write(password+'\n')
        import time
        while ph.is_ongoing(): # Letting the process finish
            time.sleep(0.1)
        return ph.get_return_code()
    # DO NOT COPY-PASTE - this is QUICK&DIRTY

What are the problems?

* This code doesn't wait until ``passwd`` actually requests the password. Different commands
  process their standard output differently, some commands discard everything in their standard
  input right before they request something (i.e. a password), so it's possible that your
  password will not be used, leaving ``passwd`` to hang (and subsequently hang your code).
* This code doesn't pass the relevant ``passwd`` output to the caller code in case an error
  occurs.

The right way
+++++++++++++

.. code-block:: python

    def passwd(username, password):
        status = ["unknown"] # hack, explained below
        def process_output(output):
            print("debug: calling process_output with {}".format(repr(output)))
            if output.strip().startswith("Enter new UNIX password:"):
                status[0] = "enter"
            elif output.strip().startswith("Retype new UNIX password:"):
                status[0] = "repeat"
            elif output.strip().startswith("passwd: password updated successfully"):
                status[0] = "success"
            else:
                # Unexpected output, let's append it to status and return it once all is done
                status.append(output)
            print("current status: {}".format(status[0]))
        ph = ProHelper(["passwd", username], output_callback=process_output)
        ph.run()
        while ph.is_ongoing():
            ph.poll() # go through output and call process_output on it
            if status[0] in ["enter", "repeat"]:
                ph.write(password+'\n')
                status[0] = "waiting" # so that we don't send the password more than necessary
            elif status[0] == "success":
                pass # By this time, we've probably finished, next cycle of "while" will not happen
            sleep(0.1)
        ph.poll() # Process leftover output so that we can check for success/failure
        # return a list of two values: 1 - True/False (success/likely failure)
        # 2 - list of all unexpected output
        return [True if status[0] == "success" else False, status[1:]]

``process_output`` function gets output from the process and sets the status.

.. note:: Why is the ``status`` variable actually a list? First of all, because we add
          all unrecognized output to it so that it can be returned later. However, if
          we didn't have this function, it'd still have to be a list. The reason is simple -
          you can't easily reassign a variable from inside a function and have the changes
          actually apply outside, but you can do operations on mutable objects (say,
          add/remove/change list items, or change attributes of an object).

Testing and understanding the limitations
+++++++++++++++++++++++++++++++++++++++++

Let's try the function the way it's expected to be used:

.. code-block:: python

    >>> passwd("pi", "password")
    debug: calling process_output with 'Enter new UNIX password: '
    current status: enter
    debug: calling process_output with '\r\nRetype new UNIX password: '
    current status: repeat
    debug: calling process_output with '\r\npasswd: password updated successfully\r\n'
    current status: success
    [True, []]

Worked out as expected! How can it break?

.. code-block:: python

    >>> passwd("pi", "")
    debug: calling process_output with 'Enter new UNIX password: '
    current status: enter
    debug: calling process_output with '\r\nRetype new UNIX password: '
    current status: repeat
    debug: calling process_output with '\r\nNo password supplied\r\nEnter new UNIX password: '
    current status: waiting
    
    # this is where the process hangs

This is certainly just the simplest way. We can also send non-string data for even more
interesting breakage! What are the possible solutions?

* Terminate the process once you get some unexpected output (can be done in ``process_output()``
* Sanity-check the inputs to the function

Whatever I choose, you can check the latest implementation of ``passwd`` in
``libs/linux/passwd.py``.
