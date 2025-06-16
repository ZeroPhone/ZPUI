from zpui_lib.apps import ZeroApp
from zpui_lib.ui import DatePicker, TimePicker

def callback(ul):
	print(ul)

class CalendarApp(ZeroApp):
    menu_name = "Calendar"
    def can_load(self):
        # needs to be able to exit the UI on platforms that are not zerophone
        return False, "app mothballed until its code is updated"

    def on_start(self):
        self.dp = DatePicker(self.i, self.o, callback=callback)
        print(self.dp.activate())

#class FirstbootWizard(ZeroApp):
#    pass
