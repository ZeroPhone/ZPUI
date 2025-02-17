from apps import ZeroApp
from ui import DatePicker, TimePicker

def callback(ul):
	print(ul)

class CalendarApp(ZeroApp):

	menu_name = "Calendar"

	def on_start(self):
		self.dp = DatePicker(self.i, self.o, callback=callback)
		print(self.dp.activate())
