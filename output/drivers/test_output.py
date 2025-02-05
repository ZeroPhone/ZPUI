#!/usr/bin/python

from ..output import GraphicalOutputDevice, CharacterOutputDevice


class Screen(GraphicalOutputDevice, CharacterOutputDevice):

    current_image = None

    __base_classes__ = (GraphicalOutputDevice, CharacterOutputDevice)

    type = ["char", "b&w"]
    cursor_enabled = False
    cursor_pos = (0, 0) #x, y

    def __init__(self):
        pass

    def display_image(self, image):
        pass

    def _display_image(self, image):
        self.device.display(image)

    def display_data_onto_image(self, *args, **kwargs):
        pass

    def display_data(self, *args):
        pass

    def home(self):
        pass

    def clear(self):
        pass

    def setCursor(self, row, col):
        pass

    def createChar(self, char_num, char_contents):
        pass

    def noDisplay(self):
        pass

    def display(self):
        pass

    def noCursor(self):
        self.cursor_enabled = False

    def cursor(self):
        self.cursor_enabled = True

    def noBlink(self):
        pass

    def blink(self):
        pass

    def scrollDisplayLeft(self):
        pass

    def scrollDisplayRight(self):
        pass

    def leftToRight(self):
        pass

    def rightToLeft(self):
        pass

    def autoscroll(self):
        pass

    def noAutoscroll(self):
        pass
