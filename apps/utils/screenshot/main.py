menu_name = "Screenshots"

import os
from time import sleep
from datetime import datetime

from zpui_lib.helpers import setup_logger, BackgroundRunner, BooleanEvent

logger = setup_logger(__name__, "info")

from ui import Menu, PrettyPrinter, GraphicsPrinter

from actions import BackgroundAction as Action

from PIL import ImageChops

i = None
o = None
context = None

screenshot_folder = "screenshots"

def take_screenshot():
    image = context.get_previous_context_image()
    if image != None:
        path = save_image(image)
        PrettyPrinter("Screenshot saved to {}".format(path), i, o)

def save_image(image):
    timestamp = datetime.now().strftime("%y%m%d-%H%M%S:%f")
    filename = "screenshot_{}.png".format(timestamp)
    path = os.path.join(screenshot_folder, filename)
    image.save(path, "PNG")
    return path

def toggle_record():
    if not recording_ongoing:
        runner = BackgroundRunner(record)
        runner.run()
    else:
        recording_ongoing.set(False)

def imgs_are_equal(i1, i2):
    return ImageChops.difference(i1, i2).getbbox() is None

recording_ongoing = BooleanEvent()
recording_ongoing.set(False)

def log_recording(filename, imgpath):
    path = os.path.join(screenshot_folder, filename)
    with open(path, 'a') as f:
        f.write(imgpath+'\n')

def record():
    recording_ongoing.set(True)
    logger.info("Recording starting")
    log_filename = "recording-{}.log".format(datetime.now().strftime("%y%m%d-%H%M%S"))
    prev_image = None
    while recording_ongoing:
        try:
            c = context.get_current_context()
            image = context.get_context_image(c)
            if image: # not doing anything if the current image isn't at least truthy
                if not prev_image or not imgs_are_equal(image, prev_image):
                    path = save_image(image)
                    logger.info("Image changed, saved to {}!".format(path))
                    log_recording(log_filename, path)
                    prev_image = image
            if not recording_ongoing:
                logger.info("Recording stopped")
                recording_ongoing.set(False)
                return True
            sleep(0.01)
        except:
            logger.exception("Recording failed!")
            recording_ongoing.set(False)
            return False
    logger.info("Recording stopped")
    recording_ongoing.set(False)
    return True

def set_context(received_context):
    global context
    context = received_context
    def menu_name_cb():
        return "Stop recording screen" if recording_ongoing else "Record screen"
    context.register_action(Action("screenshot", take_screenshot, menu_name="Screenshot", description="Takes a screenshot from previous app"))
    context.register_action(Action("record_screen", toggle_record, menu_name=menu_name_cb, description="Records the screen from currently shown app (as series of screenshots)"))

def init_app(input, output):
    global i, o
    i = input; o = output

def show_screenshot(path):
    GraphicsPrinter(path, i, o, 5, invert=False)

def list_screenshots():
    # TODO exclude recording-produced screenshots
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
