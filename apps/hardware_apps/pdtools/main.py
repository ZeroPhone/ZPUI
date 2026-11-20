from zpui_lib.ui import Menu, PrettyPrinter as Printer, Refresher, RefresherExitException
from zpui_lib.helpers import setup_logger, read_or_create_config, local_path_gen, write_config, get_platform, is_emulator, BooleanEvent, BackgroundRunner
from zpui_lib.apps import ZeroApp

from time import sleep

import smbus

local_path = local_path_gen(__name__)
logger = setup_logger(__name__, "warning")

default_config = """i2c_bus: 1
"""
config_path = local_path("config.yaml")

import fusb302
import smbus

class App(ZeroApp):

    menu_name = "PD tools"

    def init_app(self):
        self.config = read_or_create_config(config_path, default_config, self.menu_name+" app")
        # PD checker thread variable
        self.fusb_state = (-1, -1)

    def can_load(self):
        platform = get_platform()
        return "blepis" in platform or "snowdive" in platform or is_emulator()

    def callback(self):
        def ch():
            contents = [
                ["PD checker", self.ui_pd_checker],
                #["Settings", self.change_settings],
            ]
            return contents
        Menu([], self.i, self.o, contents_hook=ch, name="I2C tools menu").activate()


    # Managing the FUSB mux on Blepis/Snowdive:

    def mux_fusb_get(self):
        with open("/sys/firmware/beepy/mux_fusb", 'r') as f:
            c = f.read().strip()
        return bool(int(c))

    def mux_fusb_set(self, state):
        with open("/sys/firmware/beepy/mux_fusb", 'w') as f:
            c = f.write(str(int(state))+'\n')

    #################
    # PD checker code
    #################

    def pd_checker(self, stop_flag):
        # is ran as a thread
        self.fusb_state = (-1, -1)
        i2c = smbus.SMBus(1)
        fusb = fusb302.FUSB302(i2c)
        # init!
        fusb.host_current = 0b01
        fusb.hard_reset()
        fusb.reset()
        fusb.power()
        fusb.unmask_all()
        fusb.set_controls_sink()
        def mask_all_except_toggle(): # a little in-place helper
            fusb.i2c_write(fusb.REG_MASK, bytes((0xfe,)) )
            fusb.i2c_write(fusb.REG_MASKA, bytes((0xbf,)) )
            fusb.i2c_write(fusb.REG_MASKA, bytes((0x01,)) )
        mask_all_except_toggle()
        self.fusb_state = (-1, -1)
        if stop_flag: return # checking for immediate exit
        while not stop_flag:
            inta = fusb.interrupt_a()
            if (inta >> 6 & 0b1):
                logger.debug("FUSB int triggered")
                polarity_tuple = fusb.str_pol()
                self.fusb_state = polarity_tuple
                #print(pol, fusb.polarity_names[polarity_tuple[1]])
                if pol != (0, 0):
                    logger.debug("pol found; interrupts: " + str( list(map(bin, fusb.interrupts() )) ) )
                    fusb.set_toggle(False)
                    sleep(0.1)
                    # toggle restart
                    fusb.set_controls_sink()
                    fusb.set_toggle(False)
                    mask_all_except_toggle() # might be unnecessary
            else:
                pass # other int, somehow
            sleep(1)

    def pd_checker_thread_start(self):
        stop_flag = BooleanEvent()
        self.pd_checker_thread = BackgroundRunner(self.pd_checker, stop_flag)
        self.pd_checher_thread.run()
        return stop_flag

    def get_pd_checker_state(self):
        if self.pd_checker_thread.failed:
            logger.error("PD checker thread failed!")
            logger.error(self.pd_checker_thread.exc_info)
            raise RefresherExitException
        if not self.pd_checker_thread.running:
            logger.error("PD checker thread stopped!")
            raise RefresherExitException
        # getting data from the thread running in background
        cc, role = self.fusb_state
        role_str = fusb302.FUSB302.polarity_names[role]
        if role_str == "unknown":
            role_str = "fault"
        lines = [f"Role: '{role_str}'"]
        if role_str in ["source", "sink"]:
            lines.append(f"CC: {cc}")
        if role_str == "audio":
            lines.append("(audio adapter)")
        lines = line.center(self.o.cols)
        return lines

    def ui_pd_checker(self):
        try:
            initial_fusb_state = self.mux_fusb_get()
            # some old blepis firmwares have a FUSB mux register bit bug
            if not initial_fusb_state or "blepis" in get_platform():
                self.mux_fusb_set(True)
        except:
            logger.error("FUSB MUX read/write fail!")
            Printer("FUSB MUX read/write fail!", self.i, self.o, 2)
            return
        stop_flag = self.pd_checker_thread_start()
        r = Refresher(self.get_pd_checker_state, self.i, self.o, 1, name="PD checker refresher")
        r.activate()
        # PD checker Refresher finished, making sure we signal the thread to stop:
        stop_flag.set()
        if not initial_fusb_state:
            self.mux_fusb_set(initial_fusb_state) # setting back to False if it was False

    #def change_settings(self):
    #    settings = [["Scan range", change_range]]
    #    Menu(settings, i, o, "I2C tools app settings menu").activate()
