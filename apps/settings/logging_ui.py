i = None
o = None

from collections import OrderedDict
import logging

import zpui_lib.helpers.logger as log_system

logger_alias_map = (("root","Main launcher"),
                    ("input.input","Input system"),
                    ("apps.app_manager","App manager"),
                    ("context_manager","Context manager"),
                    ("emulator","Emulator"),
                    ("helpers.logger","Logging system"))

logger_alias_map = OrderedDict(logger_alias_map)

from zpui_lib.ui import Menu, Listbox

def get_logger_names():
    return log_system.get_logger_names()

def get_initial_logger_state():
    return log_system.get_initial_logger_state()

def prettify_logger_names(names):
    name_mapping = OrderedDict()
    for name in names:
        if name in logger_alias_map:
            # We have a defined name for this logger
            name_mapping[name] = logger_alias_map[name]
        elif name.startswith("ui."):
            # This is an UI logger
            element_name = name[len("ui."):].capitalize()
            name_mapping[name] = "UI - {}".format(element_name)
        elif name.startswith("apps."):
            # This is an app logger
            app_name, module_name = name.rsplit(".", 2)[1:]
            app_name = app_name.capitalize().replace("_", " ")
            name_mapping[name] = '{} app - {}'.format(app_name, module_name)
        elif name.startswith("input.drivers") or name.startswith("output.drivers"):
            # This is a driver logger
            driver_name = name.rsplit(".", 1)[1].capitalize().replace("_", " ")
            driver_type = name.split(".", 1)[0]
            name_mapping[name] = '{} {} driver'.format(driver_name, driver_type)
        else:
            # Fallback - name is not know and we can't yet prettify it
            name_mapping[name] = name
    return name_mapping

def get_available_levels():
    try:
        return [ value.lower() for value in logging._levelToName.values() if isinstance(value, str) ]
    except:
        return [ key.lower() for key in logging._levelNames.keys() if isinstance(key, basestring) ]

def select_loglevel(current):
    available_levels = get_available_levels()
    lb_contents = [[level.capitalize(), level] for level in available_levels]
    lb = Listbox(lb_contents, i, o, "Loglevel selection listbox")
    lb.start_pointer = available_levels.index(current.lower())
    return lb.activate()

def change_loglevel(logger_name, current_level):
    new_level = select_loglevel(current_level)
    if new_level is not None:
        assert (new_level in get_available_levels())
        log_system.LoggingConfig().set_level(logger_name, new_level)
        log_system.LoggingConfig().reload_config()

shorthands = {"NOTSET":"n"}

def get_menu_contents():
    logger_names = get_logger_names()
    initial_logger_states = get_initial_logger_state()
    pretty_logger_names = prettify_logger_names(logger_names)
    sorted_names = sorted(pretty_logger_names.items(), key=lambda x: x[1])
    for i, (name, pname) in enumerate(sorted_names):
        l = log_system.get_log_level_for_logger(name)
        orig_l = initial_logger_states.get(name, l).upper()
        sorted_names[i] = (name, pname, l, orig_l)
    mc = []
    # first pass, append the levels which have changed from the default
    for name, pname, l, orig_l in sorted_names:
        shorthand = shorthands.get(l, l[:1])
        prefix = shorthand
        if l != orig_l:
            #print(l, orig_l, name, pname)
            orig_shorthand = shorthands.get(orig_l, orig_l[:1])
            prefix = "[{}/{}]".format(shorthand, orig_shorthand)
            mc.append(["{}:{}".format(prefix, pname), lambda x=name, y=l: change_loglevel(x, y)])
    # second pass, append the levels that are set to default
    for name, pname, l, orig_l in sorted_names:
        shorthand = shorthands.get(l, l[:1])
        prefix = shorthand
        if l == orig_l:
            #print(l, orig_l, name, pname)
            mc.append(["{}:{}".format(prefix, pname), lambda x=name, y=l: change_loglevel(x, y)])
    return mc

def config_logging():
    Menu([], i, o, contents_hook=get_menu_contents).activate()
