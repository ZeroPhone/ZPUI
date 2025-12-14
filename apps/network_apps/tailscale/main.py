import requests
import subprocess
from copy import copy
from time import sleep
from threading import Event

from zpui_lib.apps import ZeroApp
from zpui_lib.actions import FirstBootAction as FBA
from zpui_lib.helpers import setup_logger, read_or_create_config, local_path_gen, ProHelper, is_emulator
from zpui_lib.ui import Menu, LoadingBar, DialogBox, TextReader, PrettyPrinter as Printer

default_config = \
"""server: none,
binary: tailscale
"""

logger = setup_logger(__name__, "info")

local_path = local_path_gen(__name__)

class TailscaleTools(ZeroApp):

    menu_name = "Tailscale"

    def init_app(self):
        self.config = read_or_create_config(local_path("config.yaml"), default_config, "Tailscale app")

    def try_tailscale(self):
        try:
            subprocess.call(self.config["binary"])
            return True
        except FileNotFoundError:
            logger.info("Failed to find tailscale binary, not loading!")
            return False

    def can_load(self):
        if is_emulator():
            return True # emulator - loading either way
        if self.try_tailscale():
            return True
        else:
            return False, "Tailscale binary not found!"

    def set_context(self, c):
        self.context = c

    def show_tailscale_failure(self, msg="tailscale failed!", info={}):
        info = copy(info); info["binary"] = self.config["binary"]; info["server"] = self.config["server"]
        text_parts = [msg] + ["{}: {}".format(k, v) for k, v in info.items()]
        text = "\n".join(text_parts)
        TextReader(text, self.i, self.o, name="Tailscale failure reader").activate()

    def is_connected(self):
        Printer("Disconnecting tailscale!", self.i, self.o, 0.1)
        pc = ProHelper([self.config["binary"], "status"], output_callback = None)
        pc.run()
        for i in range(30):
            sleep(0.1)
            pc.poll()
            s = pc.readall()
            if s: break # we got output!
            if not pc.is_ongoing(): break
        if pc.is_ongoing():
            # let's wait some extra time
            for i in range(30):
                sleep(0.1)
                pc.poll()
                s += pc.readall()
                if not pc.is_ongoing(): break
        if pc.is_ongoing():
            # throw our hands up; we simply don't know
            # TODO print output here into logs as an exception
            pc.kill_process()
            return None
        rc = pc.get_return_code()
        if rc == None: # what's going onnnnn lol
            # TODO print output here into logs as an exception
            return None
        # we must have some sort of output by now
        lines = self.clean_lines(s.split('\n'))
        if not lines:
            return False
        if lines[0].startswith("Logged out") or lines[0].startswith("Tailscale is stopped"):
            return False
        else:
            return True

    def disconnect(self):
        Printer("Disconnecting tailscale!", self.i, self.o, 0.1)
        #pc = ProHelper(["sudo", self.config["binary"], "down"], output_callback = None) # for testing on emulator
        pc = ProHelper([self.config["binary"], "down"], output_callback = None)
        pc.run()
        for i in range(30):
            sleep(0.1)
            pc.poll()
            s = pc.readall()
            if s: break # we got output!
            if not pc.is_ongoing(): break
        pc.poll()
        if pc.is_ongoing(): # we must've gotten output. however, still running = failure
            lines = self.clean_lines(s.split('\n'))
            logger.error("Process failure! Info: {}".format(str(pc.dump_info())))
            self.show_tailscale_failure(msg="Process failure! Output: {}".format(lines), info=pc.dump_info())
            pc.kill_process()
            return
        # finished (but maybe no output?)
        if pc.get_return_code() == 0:
            Printer("Success!", self.i, self.o, 2)
        else:
            lines = self.clean_lines(s.split('\n')) # could be empty but hey
            logger.error("Process failure! Info: {}".format(str(pc.dump_info())))
            self.show_tailscale_failure(msg="Process failure! Output: {}".format(lines), info=pc.dump_info())

    def clean_lines(self, lines):
        return list(filter(None, [line.strip() for line in lines]))

    def connect(self):
        Printer("Connecting tailscale!", self.i, self.o, 0.1)
        #pc = ProHelper(["sudo", self.config["binary"], "up"], output_callback = None)
        pc = ProHelper([self.config["binary"], "up"], output_callback = None)
        pc.run()
        for i in range(30):
            sleep(0.1)
            pc.poll()
            s = pc.readall()
            if s: break # we got output!
            if not pc.is_ongoing(): break
        # multiple options:
        # process finishes successfully - means we're logged in already
        # process finishes with a failure - means we can't log in
        # process keeps executing with known output, second line link: let's log in
        # process keeps executing with unknown output: failure
        if not pc.is_ongoing():
            if pc.get_return_code() == 0:
                # success!
                Printer("Success!", self.i, self.o, 1)
                return
            logger.error("Process failure! Info: {}".format(str(pc.dump_info())))
            self.show_tailscale_failure(info=pc.dump_info())
            return
        # the process has finished! let's parse the output
        logger.info("Process ongoing! Info: {}".format(str(pc.dump_info())))
        # let's extract data out of current output
        logger.info(repr(s))
        lines = self.clean_lines(s.split('\n'))
        if len(lines) != 2 or not lines[1].startswith("http"):
            # unrecognized output!
            self.show_tailscale_failure(msg="Unrecognized output: {}".format("\n".join(lines)), info=pc.dump_info())
            pc.kill_process()
            return
        url = lines[1]
        lb = LoadingBar(self.i, self.o, message=url, name="Login lb for Tailscale app")
        with lb: # loading bar is rotatin'
            pc.poll()
            while not lb.left_pressed:
                if not pc.is_ongoing():
                    # process exited!
                    rc = pc.get_return_code()
                    if rc == 0:
                        lb.set_message("Success!")
                        sleep(1)
                    else:
                        lb.set_message("Failure!")
                        sleep(1)
                        # here we show tailscale failed output
                        lines = self.clean_lines(pc.readall().split("\n"))
                        self.show_tailscale_failure(msg="Failed to login: {}".format("\n".join(lines)), info=pc.dump_info())
                    return
        # I think here we'll have exited the loadingbar through a LEFT press?
        logger.info("User interrupted login process")
        pc.kill_process()
        return

    def on_start(self):
        def get_contents():
            connected = self.is_connected()
            conn_names = {None:"Unknown", True:"UP", False:"DOWN"}
            conn_cbs = {None:None, True:self.disconnect, False:self.connect}
            mc = [["Status: {}".format(conn_names[connected]), conn_cbs[connected]],
                 # ["Peers"]
                 ]
            return mc
        Menu([], self.i, self.o, contents_hook=get_contents, name="Tailscale app main menu").activate()
