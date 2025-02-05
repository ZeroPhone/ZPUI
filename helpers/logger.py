#!/bin/env python2

import argparse
import logging
import os

from helpers.general import Singleton

try:
    import ConfigParser as configparser
except:
    import configparser  # python3


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

logger_names = set()

def setup_logger(logger_name, requested_level):
    # type: (str, str) -> logging.Logger
    global logger_names
    level = check_log_level(requested_level, logging.WARNING)
    level = LoggingConfig().get_level(logger_name, level)
    logger.debug("Logger {} will be set to {} level".format(logger_name, get_log_level_name(level)))
    l = logging.getLogger(logger_name)
    l.setLevel(level)
    logger_names.add(logger_name)
    return l

def get_logger_names():
    return list(logger_names)

def check_log_level(log_level_name, default_value):
    # type: (str, int) -> int
    """
    Verifies a logging level string - returns the requested log level
    if the supplied log level name is valid, default_value otherwise.

    >>> check_log_level("warning", logging.ERROR) == logging.WARNING
    True
    >>> check_log_level("invalid_level", logging.ERROR) == logging.ERROR
    True
    """
    try:
        return logging._checkLevel(log_level_name.upper())
    except ValueError:
        return default_value

def get_log_level_for_logger(logger_name):
    return get_log_level_name(logging.getLogger(logger_name).level)

def get_log_level_name(level):
    try:
        assert(level in logging._levelToName)
        return logging._levelToName[level]
    except AttributeError:
        assert(level in logging._levelNames)
        return logging._levelNames[level]

def on_reload(*args):
    LoggingConfig().reload_config()


class LoggingConfig(Singleton):
    """
    Keeps track of the config file, allowing us to override logging levels,
    as well as to change them while ZPUI is running.
    """

    default_config_sections = ["global"]

    def __init__(self, conf_path="log_conf.ini"):
        self.default_log_level = logging.WARNING
        self._config_file_path = conf_path
        self._app_overrides = {}
        self._load_config()

    def get_level(self, app_name, default_value=None):
        """
        Gets the recommended log level for an app, based on
        whether it's overridden from the config file, the default level and
        the global default level.
        """
        if not default_value:
            default_value = self.default_log_level

        logging_level = self._app_overrides.get(app_name, default_value)
        logger.debug("The recommended log level for {} is {}".format(app_name, get_log_level_name(logging_level)))
        return logging_level

    def set_level(self, app_name, level):
        """
        Used when calling this file with "python logger.py" and using "--set"
        to set a specific logging level in the config file.
        """
        self._app_overrides[app_name] = check_log_level(level, logging.WARNING)
        self._dispatch_log_levels()
        self.save_to_config()

    def _load_config(self):
        """
        Loads the config file and reads all log level overrides found in it.
        Creates the file if it's not found.
        """
        if not os.path.exists(self._config_file_path):
            open(self._config_file_path, 'a+').close()
            return
        config = configparser.ConfigParser()
        config.read(self._config_file_path)

        if config.has_section("global"):
            level_name = config.get("global", "default_level")
            self.default_log_level = check_log_level(level_name, logging.WARNING)

        for app_name in config.sections():
            if app_name not in self.default_config_sections:
                for key, value in config.items(app_name):
                     if key == "level":
                         self._app_overrides[app_name] = check_log_level(value, logging.NOTSET)

    def reload_config(self):
        """
        Loads the config file once again, reading and applying all config level
        overrides found in it.
        """
        self._load_config()
        self._dispatch_log_levels()

    def __str__(self):
        """
        A nice and helpful string representation, for debugging purposes.
        """
        config_str = "default log level: {}".format(logging.getLevelName(self.default_log_level))
        if not len(self._app_overrides):
            config_str += "\n\tConfig file absent or empty"
        else:
            for app_name, level in self._app_overrides.items():
               config_str += "\n\t{} : {}".format(app_name, get_log_level_name(level))
        return config_str

    def _dispatch_log_levels(self):
        """
        Actually applies the new logging levels from _app_overrides
        to the individual loggers.
        """
        for app_name, new_level in self._app_overrides.items():
            l = logging.getLogger(app_name)
            current_level = l.getEffectiveLevel()
            if current_level != new_level:
                cl_name = get_log_level_name(current_level)
                nl_name = get_log_level_name(new_level)
                logger.info("Logger {}: current level is {}, new level is {}".format(app_name, cl_name, nl_name))
                logging.getLogger(app_name).setLevel(new_level)

    def save_to_config(self):
        """
        Used when calling this file with "python logger.py" and using "--set",
        to save the config file after set_level() runs.
        """
        config = configparser.ConfigParser()
        config.add_section("global")
        config.set("global", "default_level", get_log_level_name(self.default_log_level))
        for app_name, level in self._app_overrides.items():
            config.add_section(app_name)
            config.set(app_name, "level", get_log_level_name(level))
        with open(self._config_file_path, 'w+') as config_file:
            config.write(config_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ZPUI logger configurator")
    subparsers = parser.add_subparsers(dest='cmd', help="Command")
    show_parser = subparsers.add_parser('show', help="Shows the current configuration")
    show_parser.add_argument('--path', dest='path', type=str, required=False)
    set_parser = subparsers.add_parser('set', help="Changes the log level of a given app")
    set_parser.add_argument('--name', dest='app_name', type=str, required=True)
    set_parser.add_argument('--level', dest='level', type=str, required=True)

    args = parser.parse_args()
    # Using a relative path because, when name is __main__, log_conf.ini
    # is located one directory up the tree
    conf_path = getattr(args, "path", "../log_conf.ini")
    config = LoggingConfig(conf_path = conf_path)
    if args.cmd == 'show':
        print(config)

    if args.cmd == 'set':
        config.set_level(args.app_name, args.level)
