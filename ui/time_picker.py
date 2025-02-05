from time import sleep

from ui.base_ui import BaseUIElement
from ui.canvas import Canvas

class TimePicker(BaseUIElement):

	def __init__(self, i, o, name="TimePicker"):

		BaseUIElement.__init__(self, i, o, name)

		self.c = Canvas(self.o)
		self.font = self.c.load_font("Fixedsys62.ttf", 32)

		self.current_hour = 12
		self.current_minute = 30

		self.accepted_value = False

		# Position 0 = hour, position 1 = minute
		self.position = 0

	def get_return_value(self):
		if self.accepted_value:
			return {
				'hour': self.current_hour,
				'minute': self.current_minute
			}
		else:
			return None

	def generate_keymap(self):
		return {
			"KEY_RIGHT": "move_right",
			"KEY_LEFT": "move_left",
			"KEY_UP": "increase_one",
			"KEY_DOWN": "decrease_one",
			"KEY_ENTER": "accept_value",
			"KEY_F1": "exit_time_picker"
		}

	def move_right(self):
		if self.position == 0:
			self.position = 1
		self.refresh()

	def move_left(self):
		if self.position == 1:
			self.position = 0
		self.refresh()

	def increase_one(self):
		if self.position == 0:
			if self.current_hour == 23:
				self.current_hour = 0
			else:
				self.current_hour = min(23, self.current_hour+1)

		elif self.position == 1:
			if self.current_minute == 59:
				self.current_minute = 0
			else:
				self.current_minute = min(59, self.current_minute+1)

		self.refresh()

	def decrease_one(self):
		if self.position == 0:
			if self.current_hour == 0:
				self.current_hour = 23
			else:
				self.current_hour = max(0, self.current_hour-1)
				
		elif self.position == 1:
			if self.current_minute == 0:
				self.current_minute = 59
			else:
				self.current_minute = max(0, self.current_minute-1)

		self.refresh()

	def idle_loop(self):
		sleep(0.1)

	def exit_time_picker(self):
		self.deactivate()

	def accept_value(self):
		self.accepted_value = True
		self.deactivate()

	def draw_clock(self):
		self.c.clear()

		# Draw the clock string centered on the screen
		clock_string = "{:02d}:{:02d}".format(self.current_hour, self.current_minute)
		clock_text_bounds = self.c.get_text_bounds(clock_string, font=self.font)

		width_padding = (self.c.width-clock_text_bounds[0])/2
		height_padding = (self.c.height-clock_text_bounds[1])/2
		self.c.text(clock_string, (width_padding, height_padding-2), font=self.font)

		# Draw the arrows either on the left or right side depending on whether hours or minutes are being edited
		bx = 0
		if self.position == 0:
			bx = 0
		elif self.position == 1:
			bx = self.c.width/2-width_padding+6

		# Base coordinates for arrows
		triangle_top = ((bx+width_padding+6, height_padding-5), (bx+self.c.width/2-10, height_padding-5), 
			(bx+width_padding-2+((self.c.width/2-width_padding)/2), height_padding-15))

		triangle_bottom = ((bx+width_padding+6, self.c.height-height_padding+5), (bx+self.c.width/2-10, self.c.height-height_padding+5), 
			(bx+width_padding-2+((self.c.width/2-width_padding)/2), self.c.height-height_padding+15))

		self.c.polygon(triangle_top, fill="white")
		self.c.polygon(triangle_bottom, fill="white")

		self.c.display()

	def refresh(self):
		self.draw_clock()
