## UI tests

Wondering about the funni import blocks in the beginning of each file?
The point to these tests is that they can be run as `python test_ELEMENT.py`,
in addition to being collectable by `test.sh` from ZPUI root.
This makes for quicker testing when changing something very simple in UI elements.

That said, a lot of these "import from anywhere" blocks have broken with Python3.
Don't throw them out - either leave them be or fix them.

Examples of texts where the import blocks have been fixed
(so, tests which are able to be ran from the `ui/tests/` folder):

* `test_canvas.py`
* `test_text_reader.py`
