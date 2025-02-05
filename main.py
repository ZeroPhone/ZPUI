#!/usr/bin/env python2

import argparse
import logging
import os
import signal
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler

from apps.app_manager import AppManager
from context_manager import ContextManager
from helpers import read_config, local_path_gen, logger, env, read_or_create_config, \
                    zpui_running_as_service, is_emulator
from input import input
from output import output
from actions import ContextSwitchAction
from ui import Printer
import pidcheck

rconsole_port = 9377

pid_path = '/run/zpui_pid.pid'

local_path = local_path_gen(__name__)
config_paths = ['/boot/zpui_config.json', '/boot/pylci_config.json'] if not is_emulator() else []
config_paths.append(local_path('config.json'))
#Using the .example config as a last resort
config_paths.append(local_path('default_config.json'))

input_processor = None
input_device_manager = None
screen = None
cm = None
config = None
config_path = None
app_man = None

def load_config():
    config = None
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

#Py2-3 hax
try:
    basestring
except:
    import builtins
    builtins.basestring = str

def init():
    """Initialize input and output objects"""

    global input_processor, input_device_manager, screen, cm, config, config_path
    config, config_path = load_config()

    if config is None:
        sys.exit('Failed to load any config files!')

    # Initialize output
    try:
        screen = output.init(config['output'])
    except:
        logging.exception('Failed to initialize the output object')
        logging.exception(traceback.format_exc())
        sys.exit(2)

    # Initialize the context manager
    cm = ContextManager()
    # Initialize input
    try:
        # Now we can show errors on the display
        input_processor, input_device_manager = input.init(config["input"], cm)
    except:
        logging.exception('Failed to initialize the input object')
        logging.exception(traceback.format_exc())
        Printer(['Oops. :(', 'y u make mistake'], None, screen, 0)
        sys.exit(3)

    # Tying objects together
    if hasattr(screen, "set_backlight_callback"):
        screen.set_backlight_callback(input_processor)
    cm.init_io(input_processor, screen)
    c = cm.contexts["main"]
    c.register_action(ContextSwitchAction("switch_main_menu", None, menu_name="Main menu"))
    cm.switch_to_context("main")
    i, o = cm.get_io_for_context("main")

    return i, o


def launch(name=None, **kwargs):
    """
    Launches ZPUI, either in full mode or in
    single-app mode (if ``name`` kwarg is passed).
    """

    global app_man

    i, o = init()
    appman_config = config.get("app_manager", {})
    app_man = AppManager('apps', cm, config=appman_config)

    if name is None:
        try:
            from splash import splash
            splash(i, o)
        except:
            logging.exception('Failed to load the splash screen')

        # Load all apps
        app_menu = app_man.load_all_apps()
        runner = app_menu.activate
        cm.switch_to_start_context()
    else:
        # If using autocompletion from main folder, it might
        # append a / at the name end, which isn't acceptable
        # for load_app
        name = name.rstrip('/')

        # Load only single app
        try:
            context_name, app = app_man.load_single_app_by_path(name, threaded=False)
        except:
            logging.exception('Failed to load the app: {0}'.format(name))
            input_processor.atexit()
            raise
        cm.switch_to_context(context_name)
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
        Printer(["Does Ctrl+C", "hurt scripts?"], None, screen, 0)
        status = 1
    except:
        logging.exception('A wild exception appears!')
        Printer(["A wild exception", "appears!"], None, screen, 0)
        status = 1
    else:
        logging.info('Exiting ZPUI')
        Printer("Exiting ZPUI", None, screen, 0)
    finally:
        input_processor.atexit()
        sys.exit(status)


def dump_threads(*args):
    """
    Helpful signal handler for debugging threads
    """

    logger.critical('\nSIGUSR received, dumping threads!\n')
    for i, th in enumerate(threading.enumerate()):
        logger.critical("{} - {}".format(i, th))
    for th in threading.enumerate():
        logger.critical(th)
        log = traceback.format_stack(sys._current_frames()[th.ident])
        for frame in log:
            logger.critical(frame)


def spawn_rconsole(*args):
    """
    USR2-activated debug console
    """
    try:
        from rfoo.utils import rconsole
    except ImportError:
        logger.exception("can't import rconsole - python-rfoo not installed?")
        return False
    try:
        rconsole.spawn_server(port=rconsole_port)
    except:
        logger.exception("Can't spawn rconsole!")


if __name__ == '__main__':
    """
    Parses arguments, initializes logging, launches ZPUI
    """

    # Signal handler for debugging
    signal.signal(signal.SIGUSR1, dump_threads)
    signal.signal(signal.SIGUSR2, spawn_rconsole)
    signal.signal(signal.SIGHUP, logger.on_reload)

    # Setup argument parsing
    parser = argparse.ArgumentParser(description='ZPUI runner')
    parser.add_argument(
        '--app',
        '-a',
        help='Launch ZPUI with a single app loaded (useful for testing)',
        dest='name',
        default=None)
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
    formatter = logging.Formatter(*logging_format)

    # Rotating file logs (for debugging crashes)
    rotating_handler = RotatingFileHandler(
        logging_path,
        maxBytes=logfile_size,
        backupCount=files_to_store)
    rotating_handler.setFormatter(formatter)
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
            logger.info("Skipping PID check");
        else:
            is_interactive = not zpui_running_as_service()
            do_kill = zpui_running_as_service()
            pidcheck.check_and_create_pid(pid_path, interactive=is_interactive, kill_not_stop=do_kill)

    # Launch ZPUI
    launch(**vars(args))
