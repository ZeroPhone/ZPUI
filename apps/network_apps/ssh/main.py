menu_name = "SSH settings"

import os
import subprocess
from time import sleep
from datetime import datetime

from zpui_lib.helpers import read_or_create_config, local_path_gen, save_config_gen, setup_logger, safely_backup_file
from ui import Menu, PrettyPrinter as Printer, LoadingIndicator, DialogBox
from actions import FirstBootAction
from zpui_lib.libs import systemctl

import psutil

config_filename = "config.json"
default_config = """{"ssh_key_dir":"/etc/ssh", "ssh_unit":"ssh.service",
"key_regen_commands":["dpkg-reconfigure openssh-server"]}"""

local_path = local_path_gen(__name__)
config_path = local_path(config_filename)
config = read_or_create_config(config_path, default_config, menu_name + " app")
save_config = save_config_gen(config_path)

logger = setup_logger(__name__, "info")

i = None
o = None
context = None

def init_app(input_obj, output_obj):
    global i, o
    i = input_obj
    o = output_obj

def set_context(c):
    context = c
    c.register_firstboot_action(FirstBootAction("ssh_setup", setup_ssh, depends=None, before=["wifi_setup"], not_on_emulator=True))

def setup_ssh():
    choice = DialogBox("ync", i, o, message="Regenerate SSH keys?").activate()
    if choice:
        regenerate_ssh_keys(prompt=False)
    choice = DialogBox("ync", i, o, message="Enable SSH server?").activate()
    if choice is not None:
        if choice:
            enable_ssh()
        else:
            disable_ssh()

def regenerate_ssh_keys(prompt=True):
    if prompt:
        # if prompt is true, we're being called from a user-accessible menu
        # and if that's the case, we need to add warnings
        Printer("Regenerating keys may result in your system being inaccessible over network!", i, o)
        choice = DialogBox("ncy", i, o, message="Regenerate SSH keys?").activate()
        if not choice:
            return
    try:
        with LoadingIndicator(i, o, message="Regenerating SSH keys"):
            logger.info("Regenerating SSH keys")
            ssh_dir = config["ssh_key_dir"]
            key_files = [f for f in os.listdir(ssh_dir) \
                           if os.path.isfile(os.path.join(ssh_dir, f)) \
                           and f.startswith("ssh_host") and "key" in f]
            for f in key_files:
                # moving files instead of old removal
                # this reduces damage if the operation is done by accident
                # logger.warning("Removing {}".format(f))
                safely_backup_file(ssh_dir, f)
                current_path = os.path.join(ssh_dir, f)
                y = 0
                name = "{}old{}".format(f, y)
                while name in os.listdir(ssh_dir):
                    y += 1
                    name = "{}_old{}".format(f, y)
                new_path = os.path.join(ssh_dir, name)
                os.move(current_path, new_path)
            for command in config["key_regen_commands"]:
                subprocess.call(command, shell=True)
    except:
        logger.exception("Failed to regenerate keys!")
        Printer("Failed to regenerate keys!", i, o)
        return False
    else:
        Printer("Regenerated keys!", i, o)
        return True

def disable_ssh():
    if not systemctl.bus_acquired():
       Printer("systemctl: system-wide dbus not found! ", i, o, 5)
       return
    logger.info("Disabling SSH")
    ssh_unit = config["ssh_unit"]
    systemctl.action_unit("stop", ssh_unit)
    systemctl.action_unit("disable", ssh_unit)
    logger.info("Disabled SSH")

def enable_ssh():
    if not systemctl.bus_acquired():
       Printer("systemctl: system-wide dbus not found! ", i, o, 5)
       return
    logger.info("Enabling SSH")
    ssh_unit = config["ssh_unit"]
    systemctl.action_unit("enable", ssh_unit)
    systemctl.action_unit("start", ssh_unit)
    sleep(1)
    logger.info("Enabled SSH")

def callback():
    def gen_menu_contents():
        ssh_status = any([p.name() == "sshd" for p in psutil.process_iter()])
        ssh_entry = ["Disable SSH", disable_ssh] if ssh_status \
                else ["Enable SSH", enable_ssh]
        script_menu_contents = [ssh_entry,
                                ["Regenerate keys", regenerate_ssh_keys]]
        return script_menu_contents
    Menu([], i, o, "SSH app menu", contents_hook=gen_menu_contents).activate()
