from datetime import datetime
from time import sleep
from copy import copy

from zpui_lib.ui import MockOutput, Canvas, Zone, ZoneSpacer as ZS, \
                VerticalZoneSpacer as VZS, ZoneManager
from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "info")

def setup_canvas(o):
    global icon_canvas, hh_mm_canvas, ss_canvas, button_canvas
    icon_canvas = Canvas(MockOutput(22, 8, o=o))
    hh_mm_canvas = Canvas(MockOutput(80, 30, o=o))
    ss_canvas = Canvas(MockOutput(20, 10, o=o))
    button_canvas = Canvas(MockOutput(40, 8, o=o))

counter = 0

def is_charging():
    return counter % 2

def get_battery():
    global counter
    counter += 1
    return counter

def draw_battery(value):
    icon_canvas.clear()
    icon_canvas.rectangle((2, 0, 20, 7))
    icon_canvas.rectangle((6, 0, 20, 7), fill="white")
    icon_canvas.rectangle((0, 1, 2, 6), fill="white")
    if is_charging():
        icon_canvas.text("Ch", (7, -1), fill="black")
    return copy(icon_canvas.get_image())

def get_gsm():
    return counter

def draw_gsm(value):
    icon_canvas.clear()
    icon_canvas.line((3, 1, 3, 6))
    icon_canvas.line((1, 1, 5, 1))
    icon_canvas.point(((1, 2), (5, 2)))
    offset = 7
    for x in reversed(range(6)):
        if value >= x:
            icon_canvas.line((x*2+offset, 6-x, x*2+offset, 6))
    return copy(icon_canvas.get_image())

def get_hh_mm():
    return datetime.now().strftime("%H:%M")

def get_ss():
    return datetime.now().strftime("%S")

def draw_hh_mm(value):
    hh_mm_canvas.clear()
    hh_mm_canvas.text(value, (0, 0), font=("Fixedsys62.ttf", 32))
    return hh_mm_canvas.get_image()

def draw_ss(value):
    ss_canvas.clear()
    ss_canvas.text(value, (0, 0))
    return ss_canvas.get_image()

def draw_button(text):
    button_canvas.clear()
    button_canvas.centered_text(text)
    return copy(button_canvas.get_image())

def get_button_l():
    return "Hello"

def get_button_r():
    return "World"

hh_mm_z = Zone(get_hh_mm, draw_hh_mm, name="HH_MM")
ss_z = Zone(get_ss, draw_ss, name="SS")
button_l_z = Zone(get_button_l, draw_button, name="lbutton")
button_r_z = Zone(get_button_r, draw_button, name="rbutton")
battery_z = Zone(get_battery, draw_battery, name="battery")
gsm_z = Zone(get_gsm, draw_gsm, name="gsm")

zones = {"hh_mm":hh_mm_z,
         "ss":ss_z,
         "gsm":gsm_z,
         "battery":battery_z,
         "button_l":button_l_z,
         "button_r":button_r_z}

markup = [
  [VZS(1)],
  [ZS(1), "gsm", "...", "battery"],
  [VZS(2)],
  ["hh_mm", ZS(3), "ss"],
  ["..."],
  ["...", "button_l", "...", "button_r", "..."],
  [VZS(1)]
]

def callback():
    setup_canvas(o)
    zm = ZoneManager(i, o, markup, zones)
    for x in range(5):
        zm.update()
        o.display_image(zm.get_image())
        sleep(1)
