menu_name = "ZeroMenu"

import os

from actions import Action, ContextSwitchAction, FirstBootAction
from ui import Menu, PrettyPrinter, Checkbox, Listbox
from helpers import read_or_create_config, local_path_gen, save_config_gen, setup_logger

i = None
o = None
context = None
zeromenu = None

default_config = '{"ordering":[], "excluded_actions":[], "app_open_entries":[]}'
config_filename = "config.json"

local_path = local_path_gen(__name__)
config = read_or_create_config(local_path(config_filename), default_config, menu_name+" app")
save_config = save_config_gen(local_path(config_filename))

logger = setup_logger(__name__, "warning")

def set_context(received_context):
    global context
    context = received_context
    context.request_global_keymap({"KEY_PROG2":context.request_switch})
    context.threaded = True
    context.set_target(zeromenu.activate)

def set_ordering():
    pass

def get_menu_name_for_alias(cl, alias):
    menu_names = {app["name"]:app["menu_name"] for app in cl}
    return menu_names.get(alias, None)

def app_open_entries():
    global config

    def remove_entry_menu(): # Kinda misleading, since it's a Listbox
        cl = context.list_contexts()
        gmnfa = get_menu_name_for_alias
        lc = [[gmnfa(cl, entry), entry] for entry in config["app_open_entries"] if gmnfa(cl, entry)]
        if not lc:
            PrettyPrinter("No app open entries found!", i, o, 3)
            return
        choice = Listbox(lc, i, o, name="Zeromenu app open entry removal menu").activate()
        if choice:
            config["app_open_entries"].remove(choice)
            save_config(config)

    def add_entry_menu():
        cl = context.list_contexts()
        app_context_list = [entry for entry in cl if entry["menu_name"]]
        lc = [[e["menu_name"], e["name"]] for e in app_context_list]
        lc = list(sorted(lc))
        if not lc:
            PrettyPrinter("No suitable app contexts found!", i, o, 3)
            return
        choice = Listbox(lc, i, o, name="Zeromenu app open entry addition menu").activate()
        if choice:
            config["app_open_entries"].append(choice)
            save_config(config)

    mc = [["Add an entry", add_entry_menu],
          ["Remove an entry", remove_entry_menu]]
    Menu(mc, i, o, name="Zeromenu app open entry settings menu").activate()

def manage_contents():
    global config
    cc = []
    for action in context.get_actions():
        menu_name_or_cb = action.menu_name
        menu_name = menu_name_or_cb() if callable(menu_name_or_cb) else menu_name_or_cb
        name = action.full_name
        is_excluded = action.full_name not in config["excluded_actions"]
        cc.append([menu_name, name, is_excluded])
    choice = Checkbox(cc, i, o, default_state=False, name="ZeroMenu contents checkbox").activate()
    if choice:
        for action in choice:
            state = choice[action]
            if state == False and action not in config["excluded_actions"]:
                config["excluded_actions"].append(action)
            elif state == True and action in config["excluded_actions"]:
                config["excluded_actions"].remove(action)
        save_config(config)

def settings_menu():
    mc = [["Manage contents", manage_contents],
          ["App open entries", app_open_entries]]
    #      ["Set ordering", set_ordering]]
    Menu(mc, i, o, name="ZeroMenu settings menu").activate()

def wrap_cb_in_context_switch(action, cb):
    def wrapper():
        context.request_switch(action.context)
        cb()
    return wrapper

def get_cb(action):
    if getattr(action, "func", None) is None:
        return None
    else:
        cb = action.func
        if action.will_context_switch:
            cb = wrap_cb_in_context_switch(action, cb)
    return cb

def init_app(input, output):
    global i, o, zeromenu
    i = input; o = output
    def get_contents():
        mc = []
        for name, action in context.get_actions().items():
            if isinstance(action, FirstBootAction):
                logger.debug("Action {} is a firstboot action, ignoring".format(name))
            elif name not in config["excluded_actions"]:
                menu_name_or_cb = action.menu_name
                menu_name = menu_name_or_cb() if callable(menu_name_or_cb) else menu_name_or_cb
                cb = get_cb(action)
                entry = [menu_name, cb]
                if hasattr(action, "aux_cb"):
                    entry.append(action.aux_cb)
                mc.append(entry)
        if config["app_open_entries"]:
            context_list = [entry for entry in context.list_contexts()]
            for context_alias in config["app_open_entries"]:
                menu_name = get_menu_name_for_alias(context_list, context_alias)
                if menu_name:
                    mc.append([menu_name+" app", lambda x=context_alias: context.request_switch(x)])
        mc.append(["ZM settings", settings_menu])
        return mc
    zeromenu = Menu([], i, o, name="ZeroMenu main menu", contents_hook=get_contents)
