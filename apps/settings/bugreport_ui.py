import os
import sys
import json
import threading
import traceback
from copy import deepcopy
from uuid import uuid4 as gen_uuid

from ui import Menu, DialogBox, TextReader, LoadingIndicator, PrettyPrinter, PathPicker, Checkbox
from helpers import read_or_create_config, local_path_gen, save_config_gen, setup_logger
from actions import FirstBootAction as FBA

from libs import dmesg
from libs.bugreport.bugreport import BugReport

import psutil

uuid_info_text = """UUID is the unique identifier of a bugreport sender. \
It's only used for tracking whether an error has been fixed in subsequent bugreports, \
or corellating bugreports with phones (with consent and cooperation of the phone owner) \
in case the owner inquires about the bug through other channels (IRC/Matrix/email/GitHub/etc.). \
It is randomly generated, so if you're not expecting a bugfix for your particular \
issue, feel \
free to regenerate it at any time. In the future, it will be used by ZPUI to \
query about whether there's a fix concerning a bugreport sent by particular UUID, \
and then notify the owner about it (opt-in, of course)."""

bugreport_optin_text = """ZPUI has built-in bugreport facilities to ensure error-free operation. \
These allow to automatically send somewhat-anonymized logs to ZeroPhone servers \
whenever some kind of exception happens in ZPUI (either core or apps), \
so that the bug that caused the exception can be fixed.
Your logs, once submitted, will be handled with care, processed quickly \
and fully deleted as soon as possible. You can read more  (and change your choice) \
in the Settings=>Bugreport menu."""

default_config = '{"uuid":"", "last_choices":"", "autosend":false}'
config_filename = "bugreport_config.json"

local_path = local_path_gen(__name__)
config = read_or_create_config(local_path(config_filename), default_config, "Bugreport app")
save_config = save_config_gen(local_path(config_filename))

logger = setup_logger(__name__, "info")

log_options = [
["ZPUI logs", "zpui_logs"],
["ZPUI info (config, git info)", "zpui_info"],
["ZPUI threads", "zpui_threads"],
["ZPUI screenshots", "zpui_screenshots"],
#["ZPUI contexts", "zpui_contexts"],
["dmesg output", "dmesg"],
["/var/log/ contents", "var_log"],
["Processes", "ps"],
["Custom files", "custom"]
]

i = None
o = None
git_if = None

def main_menu():
    mc = [["Send a bugreport", send_files],
          ["Manage UUID", manage_uuid],
          ["Automatic bugreports", control_autosend],
          ["Privacy policy", read_privacy_policy]]
    Menu(mc, i, o, name="Bugreport app main menu").activate()

def read_privacy_policy():
    with open(local_path("privacy_policy.txt")) as f:
       pp_text = f.read()
    TextReader(pp_text, i, o, "Bugreport app privacy policy reader", h_scroll=False).activate()

def process_choice(choice, bugreport, li):
    logger.info("Processing choice: {}".format(choice))
    if choice == "zpui_logs":
       dir = "logs/"
       logfiles = [os.path.join(dir, f) for f in os.listdir(dir) if f.startswith('zpui.log')]
       for logfile in logfiles:
           bugreport.add_file(logfile)
    if choice == "zpui_screenshots":
       dir = "screenshots/"
       bugreport.add_dir(dir)
    elif choice == "zpui_info":
       import __main__
       bugreport.add_file(__main__.config_path)
       try:
           branch = git_if.get_current_branch()
           head = git_if.get_head_for_branch(branch)[:10]
       except:
           logger.exception("Can't get git information!")
           branch = "unknown"
           head = "unknown"
       git_info = "ZPUI branch: {}; commit: {}".format(branch, head)
       bugreport.add_text(git_info, "zpui_git_info.txt")
    elif choice == "zpui_threads":
       data = []
       for th in threading.enumerate():
           data.append(str(th))
           log = traceback.format_stack(sys._current_frames()[th.ident])
           for frame in log:
               data.append(str(frame))
       bugreport.add_text("\n".join(data), "zpui_threads.txt")
    elif choice == "zpui_contexts":
       raise NotImplementedError
    elif choice == "dmesg":
       bugreport.add_text(json.dumps(dmesg.get_dmesg()), "dmesg.json")
    elif choice == "var_log":
       dir = "/var/log/"
       bugreport.add_dir(dir)
    elif choice == "ps":
       data = []
       attrs = ["cmdline", "pid", "memory_info", "memory_percent",
                "cpu_times", "cpu_percent", "exe", "name", "ionice",
                "nice", "num_threads", "username"]
       for p in psutil.process_iter():
           p_data = {}
           for attr in attrs:
              m = getattr(p, attr, "Error")
              try:
                  v = m() if callable(m) else m
              except:
                  v = "call error"
              p_data[attr] = v
           data.append(p_data)
       bugreport.add_text(json.dumps(data), "psinfo.json")
    elif choice == "custom":
        file_list = []
        def remove_file(file):
            choice = DialogBox("yn", i, o, message="Remove from list?", name="Bugreport app custom file picker remove confirmation DialogBox").activate()
            if choice:
                file_list.remove(file)
        def add_file():
            default_path = PathPicker.default_path if not file_list else file_list[-1]
            path = PathPicker(default_path, i, o, name="Bugreport app custom file picker PathPicker", display_hidden = True).activate()
            if path:
                file_list.append(path)
        def add_dir():
            default_path = PathPicker.default_path if not file_list else file_list[-1]
            path = PathPicker(default_path, i, o, dirs_only=True, name="Bugreport app custom file picker PathPicker", display_hidden = True).activate()
            if path:
                file_list.append(path)
        def get_contents():
            c = []
            for f in file_list:
                c.append([f, lambda x=f: remove_file(x)])
            c.append(["Add file", add_file])
            c.append(["Add dir", add_dir])
            return c
        m = Menu([], i, o, name="Bugreport app custom file picker menu", contents_hook=get_contents)
        m.exit_entry = ["Send", 'exit']
        with li.paused:
            m.activate()
        for path in file_list:
            try:
                bugreport.add_dir_or_file(path)
            except ValueError:
                logger.warning("Path {} is neither file nor directory, ignoring".format(path))

def send_files():
    if not config.get("uuid", None):
        generate_uuid()
    uuid = config["uuid"]
    cb_contents = deepcopy(log_options)
    if config.get("last_choices", None):
        last_choices = config.get("last_choices")
        for e in cb_contents:
            if e[1] in last_choices:
                v = last_choices[e[1]]
                if len(e) > 2:
                   e[2] = v
                elif len(e) == 2:
                   e.append(v)
                else:
                   e.append(e[0])
                   e.append(v)
    choices = Checkbox(cb_contents, i, o, name="Checkbox for selecting logs to be sent").activate()
    if not choices:
        return
    config["last_choices"] = choices
    save_config(config)
    ##### DATE_STR!~
    date_str = "ololo"
    with LoadingIndicator(i, o, message="Processing files", name="Bugreport log sending loading bar") as li:
        try:
            filename = "ZPUI_logs-{}-{}.zip".format(uuid, date_str)
            bugreport = BugReport(filename)
            selected_choices = [key for key, value in choices.items() if value]
            bugreport.add_text(json.dumps(selected_choices), "bugreport_choices.json")
            for choice in selected_choices:
                 try:
                     process_choice(choice, bugreport, li)
                 except:
                     logger.exception("Failed to process {} choice".format(choice))
                     bugreport.add_text(json.dumps(traceback.format_exc()), "choice_{}_failed.json".format(choice))
        except:
            logger.exception("Failed to collect files!")
            li.stop()
            PrettyPrinter("Failed while collecting files!", i, o, 3)
            return
        try:
            li.message = "Sending files"
            bugreport.send()
        except:
            logger.exception("Failed to send files!")
            bugreport.add_text(json.dumps(traceback.format_exc()), "bugreport_sending_failed.json")
            li.stop()
            PrettyPrinter("Failed while sending files!", i, o, 3)
            try:
                location = bugreport.store_in("/boot/")
                PrettyPrinter("Stored in {}".format(location), i, o, 3)
            except:
                PrettyPrinter("Failed to store files!", i, o, 3)
            return
        else:
            li.stop()
            PrettyPrinter("Sent files successfully!", i, o, 3)

def manage_uuid():
    mc = [["See UUID", see_uuid],
          ["New UUID", generate_uuid],
          ["What is UUID?", uuid_info]]
    Menu(mc, i, o, name="Bugreport app UUID menu").activate()

def control_autosend():
    is_autosent = config.get("autosend", False)
    d = DialogBox("yn", i, o, message="Automatically send bugreports?", name="Autosend control dialog box")
    d.set_start_option(0 if is_autosent else 1)
    choice = d.activate()
    if choice is not None:
        config["autosend"] = True if choice else False
        save_config(config)

def firstboot_log_autosend_opt_in():
    more = True
    while more: # Need to restart the DialogBox every time "learn more" option is picked
        choice = DialogBox(["y", "n", ["Learn more", "more"]], i, o, message="Automatically send ZPUI error logs for analysis & fixing?").activate()
        if choice is None:
            return False
        elif choice != "more":
            more = False
            if choice:
                logger.info("Automatic sending of bugreports enabled")
                config["autosend"] = True
                save_config(config)
            return True
        else:
            TextReader(bugreport_optin_text, i, o, "Bugreport app UUID reader", h_scroll=False).activate()
    return False

def generate_uuid():
    uuid = str(gen_uuid())
    config["uuid"] = uuid
    save_config(config)
    PrettyPrinter("Generated new UUID!", i, o, 3)

def see_uuid():
    TextReader(config["uuid"], i, o, "Bugreport app UUID reader", h_scroll=False).activate()

def uuid_info():
    TextReader(uuid_info_text, i, o, "Bugreport app UUID info reader", h_scroll=False).activate()

autosend_optin_fba = FBA("error_log_auto_send", firstboot_log_autosend_opt_in)
