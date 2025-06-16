from time import sleep

from zpui_lib.apps import ZeroApp
from zpui_lib.ui import ProgressBar, TextProgressBar, CircularProgressBar, GraphicalProgressBar, IdleDottedMessage, Throbber, \
    Listbox


class LoadingBarExampleApp(ZeroApp):
    def init_app(self):
        self.menu_name = "Loading bar test app"

        self.default_progress_bar = ProgressBar(self.i, self.o)
        self.text_progress_bar = TextProgressBar(self.i, self.o, refresh_interval=.1, show_percentage=True,
                                                 percentage_offset=0)
        self.circular_progress = CircularProgressBar(self.i, self.o, show_percentage=True)
        self.dotted_progress_bar = IdleDottedMessage(self.i, self.o)
        self.throbber = Throbber(self.i, self.o, message="Test message")
        self.graphical_progress_bar = GraphicalProgressBar(self.i, self.o)
        self.default_progress_bar = ProgressBar(self.i, self.o)
        lb_contents = [
            ["Default progress bar", self.default_progress_bar],
            ["Text progress bar", self.text_progress_bar],
            ["Dotted idle ", self.dotted_progress_bar],
            ["Circular progress ", self.circular_progress],
            ["Idle Throbber", self.throbber],
            ["Graphical Loading bar", self.graphical_progress_bar],
        ]
        self.bar_choice_listbox = Listbox(lb_contents, self.i, self.o)

    def on_start(self):
        with self.bar_choice_listbox.activate() as chosen_loading_bar:
            if hasattr(chosen_loading_bar, "progress"):
                for i in range(101):
                    chosen_loading_bar.progress = i
                    sleep(0.01)
                sleep(1)
                for i in range(101)[::-1]:
                    chosen_loading_bar.progress = i
                    sleep(0.1)
            else:
                sleep(3)
