from datetime import datetime
from time import sleep
from copy import copy

from zpui_lib.ui import MockOutput, Canvas ,Zone, ZoneSpacer as ZS, \
                 VerticalZoneSpacer as VZS, ZoneManager, crop

from zpui_lib.helpers import setup_logger, get_platform

logger = setup_logger(__name__, "info")


def setup_canvas(o):
    global icon_canvas, hh_mm_canvas, ss_canvas, button_canvas
    icon_canvas = Canvas(MockOutput(22, 8, o=o))
    hh_mm_canvas = Canvas(MockOutput(80, 30, o=o))
    ss_canvas = Canvas(MockOutput(20, 10, o=o))
    button_canvas = Canvas(MockOutput(40, 8, o=o))

counter = 0

platform = get_platform()

def is_charging():
    return counter % 2

def get_battery():
    global counter
    counter += 1
    return counter

def draw_battery(value):
    icon_canvas.clear()
    icon_canvas.rectangle((2, 0, 20, 7))
    icon_canvas.rectangle((6, 0, 20, 7), fill=icon_canvas.default_color)
    icon_canvas.rectangle((0, 1, 2, 6), fill=icon_canvas.default_color)
    if is_charging():
        icon_canvas.text("Ch", (7, -1), fill=icon_canvas.background_color)
    return copy(icon_canvas.get_image())

def get_gsm():
    return 55

def draw_gsm(value):
    icon_canvas.clear()
    icon_canvas.line((3, 1, 3, 6))
    icon_canvas.line((1, 1, 5, 1))
    icon_canvas.point(((1, 2), (5, 2)))
    offset = 7
    for x in reversed(range(6)):
        icon_canvas.line((x*2+offset, 6-x, x*2+offset, 6))
    return copy(icon_canvas.get_image())

def get_display():
    return counter % 2 == 0

def draw_display(value):
    icon_canvas.clear()
    if value:
        icon_canvas.rectangle((0, 0, 7, 5),)
        icon_canvas.line((3, 6, 4, 6))
        icon_canvas.line((1, 7, 6, 7))
    image = crop(icon_canvas.get_image(), min_height=8, align="top")
    print("display state: {} width: {}".format(value, image.width))
    return image

def get_usb():
    return counter % 3 == 1

def draw_usb(value):
    icon_canvas.clear()
    if value:
        icon_canvas.text("U", (0, -1))
    image = crop(icon_canvas.get_image(), min_height=8, min_width=8, align="bottom")
    print("usb state: {} width: {}".format(value, image.width))
    return image

def get_wifi():
    return (counter % 2 == 1, "connected", counter)

def draw_wifi(value):
    is_on, state, strength = value
    strength = counter
    offset = 9
    icon_canvas.clear()
    icon_canvas.text('W', (0, -1))
    offset=7
    strength = counter % 8
    if strength > 0:
        icon_canvas.line((offset, str(-strength), offset, 7))
    # top
    #icon_canvas.point( ((0, 1), (6, 1)), )
    #icon_canvas.line((1, 0, 5, 0), )
    # middle
    #icon_canvas.point( ((1, 3), (5, 3)), )
    #icon_canvas.line((2, 2, 4, 2), )
    # bottom
    #icon_canvas.point( ((0, 1), (6, 1)), )
    #icon_canvas.line((1, 0, 5, 0), )
    image = crop(icon_canvas.get_image(), min_height=8, min_width=10, align="bottom")
    return image

def get_hh_mm():
    return datetime.now().strftime("%H:%M")

def get_ss():
    return datetime.now().strftime("%S")

def draw_hh_mm(value):
    hh_mm_canvas.clear()
    #hh_mm_canvas.text(value, (0, 0), font=("Fixedsys62.ttf", ))
    hh_mm_canvas.text(value, (0, 0), font=("Mukta-SemiBold.ttf", 12))
    return hh_mm_canvas.get_image()

def draw_ss(value):
    ss_canvas.clear()
    ss_canvas.text(value, (0, 0))
    return ss_canvas.get_image()

def draw_button(text):
    button_canvas.clear()
    button_canvas.centered_text(text)
    return copy(button_canvas.get_image())

zones = {"hh_mm":Zone(get_hh_mm, draw_hh_mm, name="HH_MM"),
         "ss":Zone(get_ss, draw_ss, name="SS"),
         "gsm":Zone(get_gsm, draw_gsm, name="gsm"),
         "wifi":Zone(get_wifi, draw_wifi, name="wifi"),
         "usb":Zone(get_usb, draw_usb, name="usb"),
         "display":Zone(get_display, draw_display, name="display"),
         "battery":Zone(get_battery, draw_battery, name="battery"),
        }

markup = [
  [VZS(1)],
  [ZS(1), "gsm", ZS(1), "wifi", ZS(1), "usb", ZS(1), "display", "...", "battery", "hh_mm"],
  #[VZS(2)],
  #["hh_mm",], # ZS(3), "ss"],
]

def callback():
    setup_canvas(o)
    zm = ZoneManager(i, o, markup, zones)
    for x in range(5):
        zm.show()
        sleep(1)
