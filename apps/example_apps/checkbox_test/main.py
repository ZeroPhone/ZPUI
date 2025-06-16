menu_name = "Checkbox test"

from subprocess import call
from zpui_lib.ui import Checkbox, Printer

callback = None
i = None
o = None

checkbox_contents = [
["First element", '1_el', False],
["Second element", '2_el', True],
["Third element", '3_el', False],
["Fourth element xD", '4_el', True]
]

def callback():
    result = Checkbox(checkbox_contents, i, o, "Checkbox test app checkbox").activate()
    Printer(str(result), i, o, 1)
