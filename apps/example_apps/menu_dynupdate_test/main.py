menu_name = "Menu dynamic update testing"

from zpui_lib.ui import Menu

# Some globals for us
i = None # Input device
o = None # Output device

counter1 = 0
counter2 = 20

def counter_change(cnum, amount):
    global counter1, counter2
    if cnum == 1:
        counter1 += amount
    else:
        counter2 += amount
        if counter2 < 0:
            counter2 = 0

def construct_contents():
    contents = [
    ["Counter1 = {}".format(counter1)],
    ["Counter1 + 1", lambda: counter_change(1, +1) ] ]
    for i in range(counter1):
        contents.append(["Counter1:{}".format(i)])
    contents.append(["Counter2 = {}".format(counter2)])
    contents.append(["Counter2-3", lambda:counter_change(2, -3)])
    for i in range(counter2):
        contents.append(["Counter2:{}".format(i)])
    return contents

def callback():
    Menu([], i, o, "Menu update test menu", contents_hook=construct_contents).activate()
