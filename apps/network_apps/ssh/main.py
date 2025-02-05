menu_name = "SSH settings"

import os
import subprocess
from time import sleep
from datetime import datetime

from helpers import read_or_create_config, local_path_gen, save_config_gen, setup_logger
from ui import Menu, PrettyPrinter as Printer, LoadingIndicator, DialogBox
from actions import FirstBootAction
from libs import systemctl

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
       regenerate_ssh_keys()
    choice = DialogBox("ync", i, o, message="Enable SSH server?").activate()
    if choice is not None:
        if choice:
            enable_ssh()
        else:
            disable_ssh()

def regenerate_ssh_keys():
    try:
        with LoadingIndicator(i, o, message="Regenerating SSH keys"):
            logger.info("Regenerating SSH keys")
            ssh_dir = config["ssh_key_dir"]
            key_files = [os.path.join(ssh_dir, f) for f in os.listdir(ssh_dir) \
                           if os.path.isfile(os.path.join(ssh_dir, f)) \
                           and f.startswith("ssh_host") and "key" in f]
            for f in key_files:
                logger.warning("Removing {}".format(f))
                os.remove(f)
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
    logger.info("Disabling SSH")
    ssh_unit = config["ssh_unit"]
    systemctl.action_unit("stop", ssh_unit)
    systemctl.action_unit("disable", ssh_unit)
    logger.info("Disabled SSH")

def enable_ssh():
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
