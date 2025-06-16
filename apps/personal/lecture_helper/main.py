menu_name = "Lecture helper"

from datetime import datetime

from zpui_lib.ui import Menu, Printer, Refresher, IntegerAdjustInput, PathPicker, ellipsize


i = None
o = None

file_path = None
interval = 0

def setup_lecture():
    def get_contents():
        return [
        [ellipsize("File: {}".format(file_path), o.cols), change_file],
        ["Interval: {}".format(interval), change_interval],
        ["Start", start_lecture]]
    Menu([], i, o, "Lecture helper menu", contents_hook=get_contents).activate()

def change_file():
    global file_path
    file_path = PathPicker('/', i, o).activate()

def change_interval():
    global interval
    interval = IntegerAdjustInput(interval, i, o, message="Length in min.:").activate()

def start_lecture():
    if not file_path:
        Printer("File path not set!", i, o, skippable=True)
    if not interval:
        Printer("Interval not set!", i, o, skippable=True)
    if not file_path or not interval:
        return
    helper = LectureHelper(file_path, interval)
    helper.start()

class LectureHelper(object):
    refresher = None
    position = 0
    started_at = None

    def __init__(self, file, interval):
        self.filename = file
        with open(self.filename, 'r') as f:
            self.contents = [line.rstrip('\n') for line in f.readlines() if line.rstrip('\n')]
        self.contents.append("STOP")
        self.interval = interval #In minutes

    def move_left(self):
        if self.position == 0:
            self.refresher.deactivate()
            return
        self.position -= 1

    def move_right(self):
        if self.position == len(self.contents) - 1:
            return
        self.position += 1

    def get_keymap(self):
        keymap = {
          "KEY_LEFT":self.move_left,
          "KEY_RIGHT":self.move_right}
        return keymap

    def get_displayed_data(self):
        data = []
        data_rows = o.rows - 1
        current_data = self.contents[self.position]
        for i in range(data_rows):
            data.append(current_data[o.cols*i:][:o.cols*(i+1)])
        total_seconds_since_start = (datetime.now() - self.started).total_seconds()
        total_seconds_till_end = self.interval*60 - total_seconds_since_start
        minutes_till_end, seconds_till_end = map(int, (total_seconds_till_end/60, total_seconds_till_end%60))
        time_str = "{}:{}".format(minutes_till_end, seconds_till_end).center(o.cols)
        data.append(time_str)
        return data

    def start(self):
        self.started = datetime.now()
        self.refresher = Refresher(self.get_displayed_data, i, o, 1, self.get_keymap())
        self.refresher.activate()

callback = setup_lecture

def init_app(input, output):
    global i, o, callback
    i = input
    o = output
