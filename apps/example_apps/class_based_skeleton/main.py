# -*- coding: utf-8 -*-

from subprocess import call
from zpui_lib.apps.zero_app import ZeroApp
from zpui_lib.helpers import setup_logger
from zpui_lib.ui import Menu, Printer


logger = setup_logger(__name__, "info")


class SkeletonApp(ZeroApp):
    def init_app(self):
        """gets called when ZPUI is starting"""
        self.menu_name = "Class Based Skeleton"  # App name as seen in main menu while using the system
        self.main_menu_contents = [
            ["Internal command", self.call_internal],
            ["External command", self.call_external],
            ["Exit", 'exit']]

    def on_start(self):
        """gets called when application is activated in the main menu"""
        Menu(self.main_menu_contents, self.i, self.o, "Skeleton app menu").activate()

    def call_internal(self):
        Printer(["Calling internal", "command"], self.i, self.o, 1)
        logger.info("Success")

    def call_external(self):
        Printer(["Calling external", "command"], self.i, self.o, 1)
        call(['echo', 'Success'])
