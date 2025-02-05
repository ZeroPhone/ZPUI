menu_name = "Screenshots"

import os
from datetime import datetime

from ui import Menu, PrettyPrinter, GraphicsPrinter

from actions import BackgroundAction as Action

i = None
o = None
context = None

screenshot_folder = "screenshots"

def take_screenshot():
    image = context.get_previous_context_image()
    if image != None:
        timestamp = datetime.now().strftime("%y%m%d-%H%M%S")
        filename = "screenshot_{}.png".format(timestamp)
        path = os.path.join(screenshot_folder, filename)
        image.save(path, "PNG")
        PrettyPrinter("Screenshot saved to {}".format(path), i, o)

def set_context(received_context):
    global context
    context = received_context
    context.register_action(Action("screenshot", take_screenshot, menu_name="Take screenshot", description="Takes a screenshot from previous app"))

def init_app(input, output):
    global i, o
    i = input; o = output

def show_screenshot(path):
    GraphicsPrinter(path, i, o, 5, invert=False)

def list_screenshots():
    mc = []
    screenshots = [file for file in os.listdir(screenshot_folder) if file.endswith('.png')]
    for filename in screenshots:
        date_part = filename.split('_', 1)[-1].rsplit('.')[0]
        path = os.path.join(screenshot_folder, filename)
        mc.append([date_part, lambda x=path: show_screenshot(x)])
    mc = list(reversed(sorted(mc)))
    Menu(mc, i, o, name="Screenshot list ").activate()

def callback():
    list_screenshots()
    #mc = [["Screenshots", list_screenshots]]
    #Menu(mc, i, o, name="Screenshot app main menu").activate()
