#!/usr/bin/env python3

import argparse
import logging
import inspect
import os
import signal
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler

from zpui_lib.helpers import read_config, local_path_gen, logger, env, read_or_create_config, \
                    zpui_running_as_service, is_emulator, pidcheck
from zpui_lib.helpers.env import add_platform_device
from zpui_lib.helpers.logger import LoggingConfig
if __name__ == "__main__": LoggingConfig().autosave = True # "no log_conf.ini clutter by default" mechanism
from zpui_lib import hacks
from zpui_lib.ui import Printer, canvas
from zpui_lib.actions import ContextSwitchAction

from apps.app_manager import AppManager
from context_manager import ContextManager
from input import input
from output import output
import hw_combos

rconsole_port = 9377

pid_path = '/run/zpui_pid.pid'

local_path = local_path_gen(__name__)
# /boot/pylci_config.yaml might appear post-migration
config_paths = ['/boot/zpui_config.yaml', '/boot/zpui_config.json', '/boot/pylci_config.yaml', '/boot/pylci_config.json'] if not is_emulator() else []
config_paths.append(local_path('config.yaml'))
config_paths.append(local_path('config.json'))
#Using the default config as a last resort
if not is_emulator():
    config_paths.append(local_path('default_config.yaml'))

class ZPUI():
    suspended = threading.Event()

    def suspend(self):
        if not self.suspended.is_set():
            if hasattr(self.screen, "suspend"):
                self.screen.suspend()
                logger.info("Suspended screen {}".format(self.screen))
            if hasattr(self.input_processor, "suspend"):
                self.input_processor.suspend()
                logger.info("Suspended input device manager")
            self.suspended.set()

    def unsuspend(self):
        if self.suspended.is_set():
            if hasattr(self.screen, "unsuspend"):
                self.screen.unsuspend()
                logger.info("Unsuspended screen {}".format(self.screen))
            if hasattr(self.input_processor, "unsuspend"):
                self.input_processor.unsuspend()
                logger.info("Unsuspended input device manager")
            #self.cm.switch_to_context("main") # WHY, why did I do this? I forgor
            self.suspended.clear()

    def unsuspend_signal(self, *a):
        # argument catcher
        return self.unsuspend()

zpui = ZPUI()

def load_config():
    # Load config
    for config_path in config_paths:
        #Only try to load the config file if it's present
        #(unclutters the logs)
        if os.path.exists(config_path):
            try:
                logging.debug('Loading config from {}'.format(config_path))
                config = read_config(config_path)
            except:
                logging.exception('Failed to load config from {}'.format(config_path))
                config_path = None
            else:
                logging.info('Successfully loaded config from {}'.format(config_path))
                break
    # After this loop, the config_path global should contain
    # path for config that successfully loaded

    return config, config_path

default_log_config = """{"dir":"logs/", "filename":"zpui.log", "format":
["[%(levelname)s] %(asctime)s %(name)s: %(message)s","%Y-%m-%d %H:%M:%S"],
"file_size":1048576, "files_to_store":5}
"""
log_config = read_or_create_config("log_config.json", default_log_config, "ZPUI logging")
logging_dir = log_config["dir"]
log_filename = log_config["filename"]
# Making sure the log dir exists - create it if it's not
try:
    os.makedirs(logging_dir)
except OSError:
    pass
#Set all the logging parameter variables
logging_path = os.path.join(logging_dir, log_filename)
logging_format = log_config["format"]
logfile_size = log_config["file_size"]
files_to_store = log_config["files_to_store"]

# run ZPUI hacks

hacks.basestring_hack()

def init():
    """Initialize input and output objects"""

    if not getattr(zpui, "config", None):
        zpui.config, zpui.config_path = load_config()
    else:
        zpui.config_path = "pre-supplied"
    logging.info("Loaded config: {}".format(zpui.config))

    if zpui.config is None:
        sys.exit('Failed to load any config files!')

    # Get hardware manager
    zpui.input_config, zpui.output_config, zpui.device = hw_combos.get_io_configs(zpui.config)
    if zpui.device != None:
        add_platform_device(zpui.device)

    # Initialize output
    try:
        zpui.screen = output.init(zpui.output_config)
        zpui.screen.default_font = canvas.get_default_font()
        if "color" in zpui.screen.type: # screen can do color output - let's see if there's a color in config
            # either of the two parameters are possible - ui-color or ui_color; both are the same thing obvi
            color = zpui.config.get("ui_color", "")
            color = zpui.config.get("ui-color", color)
            #print("color", color)
            if color:
                canvas.global_default_color = color
            # also passing color to the screen object (used for char output)
            c = canvas.Canvas(zpui.screen) # running canvas init so that color gets processed
            if hasattr(zpui.screen, "set_color"):
                zpui.screen.set_color(c.default_color)
            zpui.screen.default_color = c.default_color
            canvas.global_default_color = c.default_color # setting the canvas-global color after it's been processed by the canvas

    except:
        logging.exception('Failed to initialize the output object')
        logging.exception(traceback.format_exc())
        sys.exit(2)

    # Initialize the context manager
    zpui.cm = ContextManager(zpui=zpui)
    # Initialize input
    try:
        # Now we can show errors on the display
        zpui.input_processor, zpui.input_device_manager = input.init(zpui.input_config, zpui.cm)
    except:
        logging.exception('Failed to initialize the input object')
        logging.exception(traceback.format_exc())
        Printer(['Oops. :(', 'y u make mistake'], None, zpui.screen, 0)
        sys.exit(3)

    # Tying objects together
    if hasattr(zpui.screen, "set_backlight_callback"):
        zpui.screen.set_backlight_callback(zpui.input_processor)
    if hasattr(zpui.screen, "reattach_callback"):
        for dname, driver in zpui.input_processor.initial_drivers.items():
            if hasattr(driver, "reattach_cbs"):
                # tying the screen's reattach callback into the input device
                driver.reattach_cbs.append(zpui.screen.reattach_callback)
                logging.info("attached screen reattach callback to driver {}".format(dname))
    zpui.cm.init_io(zpui.input_processor, zpui.screen)
    # ZeroMenu hook
    c = zpui.cm.contexts["main"]
    c.register_action(ContextSwitchAction("switch_main_menu", None, menu_name="Main menu"))
    # why is this in init()? but oh well ig
    zpui.cm.switch_to_context("main")

    i, o = zpui.cm.get_io_for_context("main")
    return i, o


def launch(name=None, all=False, **kwargs):
    """
    Launches ZPUI, either in full mode or in
    single-app mode (if ``name`` kwarg is passed).
    """

    i, o = init()
    zpui.appman_config = zpui.config.get("app_manager", {})
    zpui.app_man = AppManager('apps', zpui.cm, zpui, config=zpui.appman_config)

    if name is None:
        try:
            from splash import splash
            splash(i, o, color=canvas.global_default_color)
        except:
            logging.exception('Failed to load the splash screen')

        # Load all apps
        zpui.app_menu = zpui.app_man.load_all_apps()
        zpui.app_man.after_load()
        runner = zpui.app_menu.activate
        if "switch_to" in zpui.config:
            start_context = zpui.config.get("switch_to", "main")
            zpui.cm.unsafe_switch_to_context(start_context, do_raise = False)
        else:
            zpui.cm.switch_to_start_context()
    else:
        if is_emulator():
            c = canvas.Canvas(o)
            c.display() # black image display call to make sure the emulator window appears!
        # If using autocompletion from main folder, it might
        # append a / at the name end, which isn't acceptable
        # for load_app
        name = name.rstrip('/')
        # did the user ask to load all apps?
        if all:
            zpui.app_menu = zpui.app_man.load_all_apps()
            zpui.app_man.after_load()
        # Now, load and switch to the single app that's been summoned
        try:
            context_name, app = zpui.app_man.load_single_app_by_path(name, threaded=False)
        except:
            logging.exception('Failed to load the app: {0}'.format(name))
            zpui.input_processor.atexit()
            raise
        zpui.cm.switch_to_context(context_name)
        runner = app.on_start if hasattr(app, "on_start") else app.callback

    exception_wrapper(runner)


def exception_wrapper(callback):
    """
    This is a wrapper for all applications and menus.
    It catches exceptions and stops the system the right
    way when something bad happens, be that a Ctrl+c or
    an exception in one of the applications.
    """
    status = 0
    try:
        callback()
    except KeyboardInterrupt:
        logging.info('Caught KeyboardInterrupt')
        Printer(["Does Ctrl+C", "hurt scripts?"], None, zpui.screen, 0)
        status = 1
    except:
        logging.exception('A wild exception appears!')
        Printer(["A wild exception", "appears!"], None, zpui.screen, 0)
        status = 1
    else:
        logging.info('Exiting ZPUI')
        Printer("Exiting ZPUI", None, zpui.screen, 0)
    finally:
        zpui.input_processor.atexit()
        sys.exit(status)


def dump_threads(*args):
    """
    Helpful signal handler for debugging threads
    """

    logging.critical('\nSIGUSR received, dumping threads!\n')
    for i, th in enumerate(threading.enumerate()):
        logging.critical("{} - {}".format(i, th))
    for th in threading.enumerate():
        logging.critical(th)
        log = traceback.format_stack(sys._current_frames()[th.ident])
        for frame in log:
            logging.critical(frame)


def spawn_rconsole(*args):
    """
    USR2-activated debug console
    """
    try:
        from rfoo.utils import rconsole
    except ImportError:
        logging.exception("can't import rconsole - python-rfoo not installed? Install and try again?")
        return False
    try:
        rconsole.spawn_server(port=rconsole_port)
    except:
        logging.exception("Can't spawn rconsole!")


# log coloring code from https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output

class CustomFormatter(logging.Formatter):

    """
    A log handler that adds colors to console output,
    as well as tries to print local variables when exceptions occur.
    """

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    #format_str = "[%(levelname)s] (%(filename)s:%(lineno)d) %(asctime)s %(name)s: %(message)s" # (%(filename)s:%(lineno)d)"

    def __init__(self, fmt, datefmt, *args, colored=True, **kwargs):
        self.fmt = fmt
        self.datefmt = datefmt
        logging.Formatter.__init__(self, fmt, datefmt, *args, **kwargs)
        #self.old_format = logging.Formatter.format
        self.colored = colored
        self.set_formats()

    def set_formats(self):
        if self.colored:
            self.FORMATS = {
                logging.DEBUG: self.grey + self.fmt + self.reset,
                logging.INFO: self.grey + self.fmt + self.reset,
                logging.WARNING: self.yellow + self.fmt + self.reset,
                logging.ERROR: self.red + self.fmt + self.reset,
                logging.CRITICAL: self.bold_red + self.fmt + self.reset
            }
        else:
            self.FORMATS = {}

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.fmt)
        if record.exc_info:
            # this is where we try and print local variables
            try:
                locals = inspect.trace()[-1][0].f_locals
                locals_str = "\nlocals: {}".format(str(locals))
            except:
                pass
            else:
                if self.colored:
                    log_fmt = self.red + self.fmt + locals_str + self.reset
                else:
                    log_fmt = self.fmt + locals_str
        sub_formatter = logging.Formatter(log_fmt, self.datefmt)
        return sub_formatter.format(record)

if __name__ == '__main__':
    """
    Parses arguments, initializes logging, launches ZPUI
    """

    # Signal handler for debugging
    signal.signal(signal.SIGUSR1, dump_threads)
    signal.signal(signal.SIGUSR2, spawn_rconsole)
    signal.signal(signal.SIGHUP, logger.on_reload)
    signal.signal(signal.SIGCONT, zpui.unsuspend_signal)

    # Setup argument parsing
    parser = argparse.ArgumentParser(description='ZPUI runner')
    parser.add_argument(
        '--app',
        '-a',
        help='Launch ZPUI with a single app loaded (useful for testing)',
        dest='name',
        default=None)
    parser.add_argument(
        '--all',
        '-A',
        help='Launch ZPUI with a single app loaded (useful for testing)',
        action='store_true')
    parser.add_argument(
        '--log-level',
        '-l',
        help='The minimum log level to output',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO')
    parser.add_argument(
        '--ignore-pid',
        help='Skips PID check on startup (not applicable for emulator as it doesn\'t do PID check)',
        action='store_true')
    args = parser.parse_args()

    # Setup logging
    logger = logging.getLogger()
    formatter = CustomFormatter(*logging_format)
    formatter_nocolor = CustomFormatter(*logging_format, colored=False)

    # Rotating file logs (for debugging crashes)
    rotating_handler = RotatingFileHandler(
        logging_path,
        maxBytes=logfile_size,
        backupCount=files_to_store)
    rotating_handler.setFormatter(formatter_nocolor)
    logger.addHandler(rotating_handler)

    # Live console logging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Set log level
    logger.setLevel(args.log_level)

    # Check if another instance is running
    if not is_emulator():
        if args.ignore_pid:
            logging.info("Skipping PID check");
        else:
            is_interactive = not zpui_running_as_service()
            do_kill = zpui_running_as_service()
            try:
                pidcheck.check_and_create_pid(pid_path, interactive=is_interactive, kill_not_stop=do_kill)
            except:
                logging.error("PID check failed! Proceeding to launch nevertheless")
                logging.debug(traceback.format_exc())
                # one reason this happens is that pid_path is not available on i.e. Armbian, when running as non-root user
                # will have to maybe iterate through paths in the future? that does need the systemctl file to be modified, sadly

    # Launch ZPUI
    launch(**vars(args))
