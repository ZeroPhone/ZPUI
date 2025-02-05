.. _crash_course:

############
Crash course
############

This is a crash course on writing apps for ZPUI, with links to more in-depth explanations.

======
Basics
======

- What does a "do nothing" ZPUI app need? :ref:`One directory with two files and 5 lines of code <howto_minimal_zpui_app>`
- What does a "Hello, world" app need? :ref:`One more line of code. <howto_zpui_helloworld>`
- Can you do an app as an object? :ref:`Sure, here's how. <howto_minimal_zpui_class_app>`
- Want to experiment with the code using REPL? :ref:`Use the sandbox. <howto_zpui_app_sandbox>`

============================
Showing things on the screen
============================

- Want to display some text real quick? Use display_data.
- Want to display some text in a more user-friendly fashion, with UX bells&whistles? Use PrettyPrinter.
- Want to display an image? :ref:`Use display_image. <howto_show_image>`
- Want to display an image in a more user-friendly fashion, with UX bells&whistles? :ref:`Use GraphicsPrinter. <howto_show_image_better>`
- Want to construct an image dynamically? :ref:`Use Canvas. <howto_using_canvas>`

=============
Interactivity
=============

- Want some *very* basic interactivity? Setup some input callbacks and start an input thread.
- How do callbacks work, what's a keymap and how do you set one? :doc:`Read here. <keymap>`
- Want to make a very basic loop and allow the user to interrupt it? :ref:`Use ExitHelper. <howto_exit_loop_on_keypress>`
- Want to make a menu for your application? Use a Menu.
- Want to make a "pick any items out of many and accept" choice? :ref:`Use a Checkbox. <howto_many_out_of_many>`
- Want to make a "pick one out of many" choice? :ref:`Use a Listbox. <howto_one_out_of_many>`
- Want to make a "Yes"/"No"[/"Cancel"] choice? :ref:`Use DialogBox. <howto_confirm_a_choice>`
- Want to make a status screen? Use a Refresher.
- Want to input some text? Use UniversalInput.
- Want to adjust a number? Use IntegerAdjustInput.
- Want to pick a directory/file? :ref:`Use PathPicker. <howto_pick_a_file_dir>`
- Want to pick a date from the calendar? Use DatePicker.
- Want to pick a time? Use TimePicker.
- Want to show a lot of text on the screen? Use TextReader.
- Want to indicate that some task is in progress? :ref:`Use LoadingBar. <howto_show_progress>`
- Want to indicate a task is in progress, with a progress estimate? :ref:`Use ProgressBar. <howto_show_progress_with_percentage>`
- Want to make an UI element react to more buttons? :ref:`Here's how you do that. <keymap_for_custom_ui>`

=============
App internals
=============

- Want to add logging? It's very easy - :ref:`here's a snippet for adding logging. <howto_add_logging>`
- Want to include some resource files with your app - i.e. sounds? :ref:`Here's how to access them the proper way. <howto_local_path>`
- Want to have a place to store variables for your app? :ref:`Here's a snippet to use a config file. <howto_config_file>`
- Want to learn about things you should do while writing an app? We have some guidelines :ref:`here <howto_readability>` and :ref:`here <howto_improve_support>`.
- Want to learn about things you should *not* do while writing an app? :ref:`Here are some more examples. <howto_things_not_to_do>`
- Want to run things on app startup/launch/in the background? :ref:`Here are the basics of that. <howto_run_tasks_for_app>`


