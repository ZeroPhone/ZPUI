from time import sleep

from apps import ZeroApp
from ui import Refresher, NumpadNumberInput, Canvas, MockOutput, FunctionOverlay, \
   offset_points, get_bounds_for_points, expand_coords, multiply_points, check_coordinates, \
   convert_flat_list_into_pairs as cflip
from ui.base_ui import BaseUIElement
from ui.base_view_ui import BaseView

import graphics
from views import InputScreenView


class InputScreen(NumpadNumberInput):

    message = "Input number:"
    default_pixel_view = "InputScreenView"
    def __init__(self, i, o, *args, **kwargs):
        kwargs["message"] = self.message
        kwargs["value"] = "00000000000000000000000000000000000000000000000000000000012345"
        NumpadNumberInput.__init__(self, i, o, *args, **kwargs)

    def generate_views_dict(self):
        d = NumpadNumberInput.generate_views_dict(self)
        d.update({"InputScreenView":InputScreenView})
        return d


class StatusScreen(Refresher):

    arrow_x = 15
    arrow_y = 40
    handset_x = 2
    handset_y = 10
    arrow_offset = 2
    counter = 0
    number_frame = (10, 45, "-10", "-1")
    number_height = 16
    number_font = ("Fixedsys62.ttf", number_height)

    def __init__(self, *args, **kwargs):
       Refresher.__init__(self, self.show_status, *args, **kwargs)
       self.c = Canvas(self.o)
       self.prepare_number()
       self.predraw_arrow()
       self.predraw_cross()
       self.predraw_handset()
       self.status = {"number":"25250034", "accepted":True, "time":385}

    def prepare_number(self):
       frame_coords = check_coordinates(self.c, self.number_frame)
       nw, nh = get_bounds_for_points(cflip(frame_coords))
       self.number_c = Canvas(MockOutput(width=nw, height=nh, device_mode=self.o.device_mode))

    def predraw_arrow(self):
       aw, ah = get_bounds_for_points(graphics.arrow)
       arrow_c = Canvas(MockOutput(width=aw, height=ah, device_mode=self.o.device_mode))
       arrow_c.polygon(graphics.arrow, fill="white")
       self.arrow_img = arrow_c.get_image()

    def predraw_cross(self):
       aw, ah = get_bounds_for_points(graphics.cross)
       cross_c = Canvas(MockOutput(width=aw, height=ah, device_mode=self.o.device_mode))
       cross_c.polygon(graphics.cross, fill="white")
       self.cross_img = cross_c.get_image()

    def predraw_handset(self):
       handset = multiply_points(graphics.phone_handset, 2)
       aw, ah = get_bounds_for_points(handset)
       handset_c = Canvas(MockOutput(width=aw, height=ah, device_mode=self.o.device_mode))
       handset_c.polygon(handset, fill="white")
       self.handset_img = handset_c.get_image()

    def draw_arrow(self, c, flipped=False):
       coords = (self.arrow_x, self.arrow_y, self.arrow_x+self.arrow_img.width, self.arrow_y+self.arrow_img.height)
       clear_coords = expand_coords(coords, self.arrow_offset)
       c.clear(clear_coords)
       img = self.arrow_img if not flipped else self.arrow_img.rotate(180)
       c.image.paste(img, (self.arrow_x, self.arrow_y))

    def draw_cross(self, c, flipped=False):
       coords = (self.arrow_x, self.arrow_y, self.arrow_x+self.cross_img.width, self.arrow_y+self.cross_img.height)
       clear_coords = expand_coords(coords, self.arrow_offset)
       c.clear(clear_coords)
       c.image.paste(self.cross_img, (self.arrow_x, self.arrow_y))

    def draw_handset(self, c, flipped=False):
       coords = (self.handset_x, self.handset_y, self.handset_x+self.handset_img.width, self.handset_y+self.handset_img.height)
       c.image.paste(self.handset_img, (self.handset_x, self.handset_y))

    def get_status(self):
       states = ["incoming", "outgoing", "missed"]
       self.status["state"] = states[self.counter]
       self.counter += 1
       if self.counter == 3: self.counter = 0
       return self.status

    def draw_state(self, c, status):
       if status["state"] == "incoming":
           self.draw_arrow(c, flipped=True)
       elif status["state"] == "outgoing":
           self.draw_arrow(c)
       elif status["state"] == "missed":
           self.draw_cross(c)

    def draw_text_state(self, c, status):
       if not status["accepted"]:
           self.c.text(status["state"].capitalize(), (30, 9), font=(self.number_font[0], 16))
       else:
           status["time"] = status["time"] + 1
           time_str = "{:02d}:{:02d}".format(*divmod(status["time"], 60))
           self.c.text(time_str, (30, 9), font=(self.number_font[0], 16))

    def draw_number(self, c, status):
       self.number_c.clear()
       self.number_c.centered_text(status["number"], font=self.number_font)
       c.image.paste(self.number_c.image, self.number_frame[:2])
       c.rectangle(self.number_frame)

    def show_status(self):
       self.c.clear()
       status = self.get_status()
       self.draw_number(self.c, status)
       self.draw_handset(self.c)
       self.draw_state(self.c, status)
       self.draw_text_state(self.c, status)
       return self.c.get_image()


class PhoneApp(ZeroApp):

    menu_name = "Phone"

    def __init__(self, *args, **kwargs):
        ZeroApp.__init__(self, *args, **kwargs)
        self.input_screen = InputScreen(self.i, self.o)
        self.insc_overlay = FunctionOverlay({"KEY_F1":"deactivate", "KEY_F2":"backspace", "KEY_ENTER":self.insc_options}, labels=["Cancel", "Menu", "Bckspc"])
        self.insc_overlay.apply_to(self.input_screen)
        self.status_screen = StatusScreen(self.i, self.o, keymap={"KEY_ANSWER":self.accept_call, "KEY_HANGUP":self.reject_call})

    def insc_options(self):
        self.switch_to_status_screen()

    def get_context(self, c):
        self.context = c

    def switch_to_input_screen(self, digit=None):
        self.input_screen.activate()

    def switch_to_status_screen(self, digit=None):
        self.status_screen.activate()

    def accept_call(self):
        self.status_screen.status["accepted"] = True

    def reject_call(self):
        self.status_screen.status["accepted"] = False

    def on_call(self):
        self.c.request_switch()
        self.show_call_status()

    def get_call_status(self):
        raise NotImplementedError

    def show_call_status(self):
        status = self.get_call_status()
        pass

    def on_start(self):
        self.switch_to_input_screen()
