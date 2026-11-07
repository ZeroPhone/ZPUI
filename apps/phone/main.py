from subprocess import call as os_call
from time import sleep
import traceback

from zpui_lib.ui import Refresher, Menu, DialogBox, TextReader, PrettyPrinter
from zpui_lib.apps import ZeroApp
#from zpui_lib.ui.experimental import NumberKeypadInputLayer
from zpui_lib.helpers import setup_logger, BackgroundRunner, ExitHelper, BooleanEvent, \
                              read_or_create_config, local_path_gen, save_config_method_gen

from gi.repository import GLib

import ModemWatcher

logger = setup_logger(__name__, "warning")

default_config = """app_enabled: false"""
config_filename = "config.yaml"

local_path = local_path_gen(__name__)


class PhoneApp(ZeroApp):
    menu_name = "Phone"

    def init_app(self):
        # connect to phone interface here
        self.config = read_or_create_config(local_path(config_filename), default_config, self.menu_name+" app")
        self.save_config = save_config_method_gen(self, local_path(config_filename))
        if self.config.get("app_enabled", False):
            # activating the app for the purposes of showing up in the main menu
            self.callback = self.default_callback
        else:
            return # no more init until we've figured out that the app can run for sure
        self.modem_available = BooleanEvent()
        self.connection_success = BooleanEvent()
        self.info_list = []
        self.mw = None
        try:
            self.mw = ModemWatcher.ModemWatcher(self.modem_added_alert, self.info_callback)
        except:
            logger.exception("ModemWatcher start failed!")
        else:
            self.connection_success.set()
        self.launch_glib_thread()

    def info_callback(self, str, obj):
        self.info_list.append(str)
        logger.info(str)

    def modem_added_alert(self, modem_obj, is_added):
        self.modem_available.set(is_added)
        self.path = obj.get_object_path() if is_added else ""

    def set_context(self, c):
        self.i.set_maskable_callback("KEY_ANSWER", self.process_answer_key)
        self.i.set_nonmaskable_callback("KEY_HANGUP", self.process_hangup_key)
        self.context = c
        self.context.set_provider("settings_phone", self.settings_phone)

    def settings_phone(self):
        def get_mc():
            mc = [
                ["Enabled: "+("ON" if self.config.get("app_enabled", False) else "OFF"), self.toggle_app]
            ]
            return mc
        Menu([], self.i, self.o, contents_hook=get_mc, name="Phone settings menu").activate()

    settings_phone.name = "Phone app settings"

    def toggle_app(self):
        self.config["app_enabled"] = not self.config.get("app_enabled", False)
        PrettyPrinter("App will be available after ZPUI restart", self.i, self.o, 2)
        self.save_config()

    def process_answer_key(self):
        self.context.request_switch()
        if self.is_in_call():
            self.ui_answer()
        else:
            self.ui_call()

    def process_hangup_key(self):
        pass

    def ui_answer(self):
        #No context switching as for now, so all we can do is
        #answer call is there's an active one
        pass

    def ui_hangup(self):
        pass

    def ui_status(self):
        text = "\n".join(reversed(self.info_list))
        TextReader(text, self.i, self.o, name="Phone app status monitor").activate()
        #Refresher(self.ui_status_func, self.i, self.o).activate()

    def ui_status_func():
        return ["Idle"]

    def ui_call(number):
        Printer("Calling {}".format(number), self.i, self.o, 0)
        logger.error("Function stopped executing")

    def call_view(self):
        keymap = {"KEY_ANSWER":[call, "value"]}
        #NumberKeypadInputLayer(i, o, "Call number", keymap, name="Phone call layer").activate()

    def wait_for_connection():
        eh = ExitHelper(i).start()
        while eh.do_run() and init.running and not init.failed:
            sleep(1)
        eh.stop()

    def default_callback(self, counter=0):
        contents = [["Status", self.ui_status],
                    #["Call", self.ui_call]
                    ]
        Menu(contents, self.i, self.o).activate()

    def launch_glib_thread(self):
        self.br = BackgroundRunner(self.glib_runner)
        self.br.run()

    def glib_runner(self):
        main_loop = GLib.MainLoop()
        try:
            main_loop.run()
        except KeyboardInterrupt:
            pass


