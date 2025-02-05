# Serge Spraiter 20190124
import math
from decimal import *

from time import sleep
from threading import Event
from ui import Canvas, DialogBox

menu_name = "Calculator"

i = None # Input device
o = None # Output device

# constants
exit_app = Event()
do_update = Event()
waiting = Event()
blink = Event()
help_lines = ["0-9=digit/oper  ",
              "v,^=next/prev   ",
              "<=exit OK=C >=C1",
              "F5=help        v",
              "<,>=oper page  ^",
              "F1=deg     F2=MC",
              "Send=MS   End=M+",
              "Pg^=MR    Pgv=M-",
             # 0123456789abcdef
             ]

# globals
mode = None
values = None
dir = None
help_page = None
degree = None
blink_count = 0.0

columns = None
char_height = None
font1 = None

def init_app(input, output):
    global i, o
    i = input; o = output

# decimal
def add(num1, num2):
    return num1 + num2

def sub(num1, num2):
    return num1 - num2

def mul(num1, num2):
    return num1 * num2

def div(num1, num2):
    return num1 / num2

def pow(num1, num2):
    return num1 ** num2

def percent(num1, num2):
    return num1 * num2 / 100

def one_x(num1):
    return Decimal(1) / num1

def square(num1):
    return num1 * num1

def mod(num1, num2):
    return num1 % num2

def rem(num1, num2):
    return num1 // num2

# float
def to_radian(num1):
    return math.pi * num1 / 180

def sin(num1):
    if degree == False:
        return math.sin(float(num1))
    else:
        return math.sin(to_radian(float(num1)))

def cos(num1):
    if degree == False:
        return math.cos(float(num1))
    else:
        return math.cos(to_radian(float(num1)))

def tan(num1):
    if degree == False:
        return math.tan(float(num1))
    else:
        return math.tan(to_radian(float(num1)))

def to_degree(num1):
    return 180.0 * num1 / math.pi

def asin(num1):
    if degree == False:
        return math.asin(float(num1))
    else:
        return to_degree(math.asin(float(num1)))

def acos(num1):
    if degree == False:
        return math.acos(float(num1))
    else:
        return to_degree(math.acos(float(num1)))

def atan(num1):
    if degree == False:
        return math.atan(float(num1))
    else:
        return to_degree(math.atan(float(num1)))

def hsin(num1):
    return math.sinh(float(num1))

def hcos(num1):
    return math.cosh(float(num1))

def htan(num1):
    return math.tanh(float(num1))

def pi():
    return math.pi

def e():
    return math.e

# def factorial(num1):
#     return math.factorial(float(num1))

class Oper:
    def __init__(self, short, full, func, parm=1):
        self.short = short
        self.full = full
        self.func = func
        self.parm = parm
        pass

# page1
oper1 = [Oper("1+ ", "+", add, 2),          # 1, +
         Oper("2- ", "-", sub, 2),          # 2, -
         Oper("3% ", "%", percent, 2),      # 3, %
         Oper("4* ", "*", mul, 2),          # 4, *
         Oper("5/ ", "/", div, 2),          # 5, /
         Oper("6/x", "1/x", one_x),         # 6, 1/x
         Oper("7^2", "square", square),     # 7, ^2
         Oper("8sq", "sqrt", Decimal.sqrt), # 8, sqr
         Oper("9^y", "pow", pow, 2),        # 9, x^y
         Oper("*ln", "ln", Decimal.ln),     # #, ln
         Oper("0ex", "exp", Decimal.exp),   # 0, exp
         Oper("#pi", "pi",  pi, 0),         # *, pi
         ]
# page2
oper2 = [Oper("1si", "sin", sin),           # 1, sin
         Oper("2co", "cos", cos),           # 2, cos
         Oper("3ta", "tan", tan),           # 3, tan
         Oper("4as", "asin", asin),         # 4, asin
         Oper("5ac", "acos", acos),         # 5, acos
         Oper("6at", "atan", atan),         # 6, atan
         Oper("7hs", "sinh", hsin),         # 7, sinh
         Oper("8hc", "cosh", hcos),         # 8, cosh
         Oper("9ht", "tanh", htan),         # 9, tanh
         Oper("*mo", "mod", mod, 2),        # #, mod
         Oper("0re", "rem", rem, 2),        # 0, rem
         Oper("#e ", "e", e, 0),            # *, e
         ]

class Values:
    def __init__(self):
        self.clear()

    def clear(self):
        self.number = ["", "", None, ""] # number1, number2, memory, result
        self.oper = 0
        self.page = oper1

    def get_index(self):
        if mode == 0:  # number1
            return 0
        elif mode == 2:  # number2
            return 1
        else: # operation
            return -1

    def clear_number(self):
        index = self.get_index()
        if index >= 0: # number1,2
            self.number[index] = ""
        do_update.set()

    def delete_digit(self):
        index = self.get_index()
        if index >= 0: # number1,2
            s = str(self.number[index])
            if len(s) == 1:
                self.number[index] = ""
            else:
                self.number[index] = s[0:-1]
        else: # operation
            self.page = oper2
        do_update.set()

    def add_digit(self, index, key):
        s = str(self.number[index])
        if len(s) < columns:
            self.number[index] = s + key

    def add_sign(self, index):
        s = str(self.number[index])
        if not s.startswith('-'):
            if s != "":
                if len(s) < columns:
                    self.number[index] = '-' + s
                else:
                    self.number[index] = '-' + s[0:-1]
        else:
            self.number[index] = s[1:]

    def add_dot(self, index):
        s = str(self.number[index])
        if s.find('.') < 0:
            if s == "":
                self.number[index] = '0.'
            else:
                if len(s) < columns:
                    self.number[index] = s + '.'

    def save(self):
        s = str(self.number[3]) # result
        if s == "E":
            return
        self.number[2] = s # to memory
        do_update.set()

    def read(self):
        index = self.get_index()
        if index >= 0: # number1,2
            if self.number[2] != None:
                self.number[index] = str(self.number[2])  # memory
                do_update.set()

    def clear_memory(self):
        self.number[2] = None
        do_update.set()

    def add_memory(self):
        s = str(self.number[3])  # result
        if s == "E" or s == "": # nothing to add
            return
        num2 = Decimal(s)
        if self.number[2] == None:  # memory
            num1 = Decimal("0")
        else:
            num1 = Decimal(str(self.number[2]))
        self.number[2] = add(num1, num2)
        do_update.set()

    def sub_memory(self):
        s = str(self.number[3])  # result
        if s == "E" or s == "":  # nothing to add
            return
        num2 = Decimal(s)
        if self.number[2] == None:  # memory
            num1 = Decimal("0")
        else:
            num1 = Decimal(str(self.number[2]))
        self.number[2] = sub(num1, num2)
        do_update.set()

def show(lines):
    if len(lines) < 4:
        max = len(lines)
    else:
        max = 4
    index = values.get_index()
    if index == 1:
        index = 2 # row 3
    c = Canvas(o)
    for n in range(max):
        y = n * char_height
        c.text(lines[n], (0, y), font=font1)
        if n == index and blink.isSet(): # row 0 or 3 && blink
            c.invert_rect((127 - 8, y + char_height - 4, 127, y + char_height - 1))
    c.display()

def help():
    waiting.set()
    blink.clear()
    start = help_page * 4
    show(help_lines[start:start + 4])

def exit():
    index = values.get_index()
    if index < 0: # operation
        values.page = oper1
        do_update.set()
        return
    waiting.set()
    blink.clear()
    choice = DialogBox("yn", i, o, message="Exit?").activate()
    waiting.clear()
    if choice:
        exit_app.set()
    else:
        do_update.set()
        set_keymap()

def toggle_degree():
    global degree
    degree = not degree
    do_update.set()

def next_mode(where):
    global mode, dir, help_page
    if waiting.isSet():
        help_page = help_page + where
        if help_page < 0:
            help_page = 0
            return
        max = (len(help_lines) // 4) - 1
        if help_page > max:
            help_page = max
        help()
        return
    dir = where # save direction
    mode += dir # 0=number1, 1=operation, 2=number2
    if mode > 2:
        mode = 2
    elif mode < 0:
        mode = 0
    do_update.set()

def process_key(key):
    index = values.get_index()
    if index >= 0:  # number1,2
        if key >= '0' and key <= '9':
            values.add_digit(index, key)
        elif key == '-':
            values.add_sign(index)
        elif key == '.':
            values.add_dot(index)
    else:  # operation
        if key == '-':
            values.oper = 9
        elif key == '0':
            values.oper = 10
        elif key == '.':
            values.oper = 11
        else: # 1-9
            values.oper = ord(key) - ord('1')
        if values.page[values.oper].parm == 2:
            next_mode(dir) # continue
        else:
            next_mode(-dir)  # return to previous
    do_update.set()

def set_keymap():
    keymap = {"KEY_ENTER": values.clear_number, # clear number
              "KEY_LEFT": exit, # exit / oper1
              "KEY_RIGHT": values.delete_digit,  # delete last digit / oper2
              "KEY_UP": lambda: next_mode(-1),   # prev mode/ help
              "KEY_DOWN": lambda: next_mode(+1), # next mode / help
              "KEY_ANSWER": values.save,         # save to memory
              "KEY_F3": values.read,             # read from memory
              "KEY_HANGUP": values.add_memory,   # add to memory
              "KEY_F4": values.sub_memory,       # sub from memory
              "KEY_F2": values.clear_memory,
              "KEY_F1": toggle_degree,
              "KEY_F5": help,
              "KEY_*": lambda: process_key('-'),
              "KEY_#": lambda: process_key('.'),
              }
    for a in range(10):
        keymap["KEY_{}".format(a)] = lambda x=a: process_key(str(x))
    i.stop_listen()
    i.set_keymap(keymap)
    i.listen()

def cursor(interval):
    global blink_count
    blink_count = blink_count + interval
    if blink_count > 0.55:
        blink_count = 0
        if blink.isSet():
            blink.clear()
        else:
            blink.set()
        do_update.set()

def fit_result(result, max):
    if len(result) <= max: # fit?
        return result
    start = result.find('.')
    if start < 0 or start > max: # more than 15 digits: xx, xx.yy, xx.yyE+zz
        return 'E'
    result = result.upper()
    end = result.find('E')
    if end < 0:  # xx.yy
        return result[0:max]  # cut after .
    exp = result[end:len(result)]  # E+zz
    ln = len(exp)
    if start + ln >= max: # unable to fit E+zz
        return 'E'
    return result[0:max - ln] + exp

def get_lines():
    index = values.get_index()
    if index >= 0:  # number1,2
        if values.page[values.oper].parm == 0: # set pi, e first
            values.number[index] = str(values.page[values.oper].func())
        l1 = "{:>16}".format(values.number[0])  # number1
        if values.number[2] != None:  # memory
            mem = 'M'
        else:
            mem = ' '
        if degree == True:  # degrees?
            deg = 'deg'
        else:
            deg = 'rad'
        if values.page[values.oper] == None:
            l2 = ""
        else:
            l2 = "{} {}{:>11}".format(mem, deg, values.page[values.oper].full) # operation
        l3 = "{:>16}".format(values.number[1])  # number2
        try:
            if str(values.number[0]) == "": # first value
                num1 = Decimal("0")
            else:
                num1 = Decimal(values.number[0])
            if str(values.number[1]) == "": # second value
                num2 = Decimal("0")
            else:
                num2 = Decimal(values.number[1])
            result = ""
            if values.page[values.oper] != None:
                if values.page[values.oper].parm == 2:
                    result = str(values.page[values.oper].func(num1, num2))
                elif values.page[values.oper].parm == 1:
                    if index == 0:
                        num = num1
                    else:
                        num = num2
                    result = str(values.page[values.oper].func(num)) # from cursor
        except:
            result = 'E'
        values.number[3] = fit_result(result, 16) # not more than 16 chars
        l4 = "{:>16}".format(values.number[3]) # result
        return [l1, l2, l3, l4, ]
    # operation
    if values.page == oper1:
        left = " "
        right = ">"
    else:
        left = "<"
        right = " "
    return ["{} {} {} {} {}".format(left, values.page[0].short, values.page[1].short, values.page[2].short, right),
            "  {} {} {}".format(values.page[3].short, values.page[4].short, values.page[5].short),
            "  {} {} {}".format(values.page[6].short, values.page[7].short, values.page[8].short),
            "  {} {} {}".format(values.page[9].short, values.page[10].short, values.page[11].short),]

def init():
    global columns, char_height, font1, mode, dir, degree, blink_count, waiting, help_page, values
    getcontext().prec =  15
    columns = 16  # display width in chars
    char_height = int(o.height / 4)
    c1 = Canvas(o)
    font1 = c1.load_font("Fixedsys62.ttf", char_height)
    mode = 0  # number1
    dir = +1 # move down
    degree = False # radians
    blink_count = 0.0
    blink.clear()
    waiting.clear()
    help_page = 0
    values = Values()

def callback():
    init()
    help()
    set_keymap()
    exit_app.clear()
    do_update.clear()
    while not exit_app.isSet():
        if do_update.isSet():
            do_update.clear()
            waiting.clear()
            lines = get_lines()
            show(lines)
        sleep(0.01)
        if not waiting.isSet():
            cursor(0.01)
