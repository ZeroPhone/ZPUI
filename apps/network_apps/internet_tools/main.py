import requests
from time import sleep
from threading import Event

from apps import ZeroApp
from actions import FirstBootAction as FBA
from helpers import setup_logger, read_or_create_config, local_path_gen
from ui import Menu, PrettyPrinter as Printer, LoadingBar, DialogBox

default_ip_source = "https://icanhazip.com"

default_config = \
"""
{
"ip_source":\""""+default_ip_source+"""\",
"connectivity_sources": [
  "https://example.org/",
  "https://zerophone.org/"
]
}
"""

logger = setup_logger(__name__, "info")

local_path = local_path_gen(__name__)
config = read_or_create_config(local_path("config.json"), default_config, "Internet tools app")

class InternetTools(ZeroApp):

    menu_name = "Internet tools"

    def set_context(self, c):
        self.context = c
        self.context.register_firstboot_action(FBA("check_connectivity", self.firstboot))

    def firstboot(self):
        return self.check_connectivity_ui()

    def check_connectivity_ui(self):
        lb = LoadingBar(self.i, self.o, message="Checking connectivity", name="Connectivity check loadingbar")
        with lb:
            result = self.check_connectivity(cancel_setter = lb.set_on_left)
            if result is False:
                lb.set_message("No connectivity!")
                sleep(1)
        return result

    def check_connectivity(self, cancel_setter = None):
        s = None
        was_cancelled = Event()
        if cancel_setter:
            def cancel_cb():
                # Untested
                s.close()
                was_cancelled.set()
            cancel_setter(cancel_cb)
        sources = config.get("connectivity_sources", [default_ip_source])
        s = requests.Session()
        try:
            r = s.get(sources[0]) # no "get from multiple sources" yet
        except requests.ConnectionError:
            return False
        if was_cancelled.isSet():
            return None
        success = True if r.status_code in range(200, 300) else False
        return success

    def get_ip(self):
        try:
            r = requests.get(config.get("ip_source", default_ip_source))
        except requests.ConnectionError:
            return False
        if r.status_code in range(200, 300):
            return r.text.strip()
        else:
            return None

    def get_ip_ui(self):
        lb = LoadingBar(self.i, self.o, message="Getting IP", name="Ip check loadingbar for internet tools app")
        with lb:
            ip = self.get_ip()
            if not ip:
                lb.set_message("Can't get IP!")
                sleep(1)
                return
        Printer(ip, self.i, self.o, 3)

    def on_start(self):
        mc = [["Check connectivity", self.check_connectivity_ui],
              ["Get IP", self.get_ip_ui]
             ]
        Menu(mc, self.i, self.o, name="Internet tools app main menu").activate()
