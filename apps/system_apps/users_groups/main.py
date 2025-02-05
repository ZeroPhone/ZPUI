menu_name = "Users&groups"

import os
import pwd

from ui import Menu, UniversalInput, PrettyPrinter as Printer, DialogBox
from actions import FirstBootAction
from helpers import setup_logger

from libs.linux.passwd import passwd

logger = setup_logger(__name__, "warning")

i = None
o = None
context = None

home_dir = "/home/"

def set_context(c):
    global context
    context = c
    c.register_firstboot_action(FirstBootAction("change_password", change_user_password, depends=None, not_on_emulator=True))

def change_user_password():
    """
    User-friendly function to be used on first boot for changing user passwords
    """
    usernames = get_nonroot_nonsystem_users()
    if len(usernames) == 0:
        logger.warning("Can't detect any users! Changing root password instead")
        usernames = ["root"]
    for name in usernames:
        db = DialogBox("yn", i, o, message="Change password for \"{}\"?".format(name), name="FB; User&pw app dialogbox for {} pw change".format(name))
        choice = db.activate()
        if choice:
            result = change_password(name)
            if result is None:
                return None
            elif result:
                logger.info("Changed password for {}".format(name))
                return True
            else:
                logger.info("Failed changing password for {}".format(name))
                return False
        return None

def get_nonroot_nonsystem_users(users = None):
    """
    Get all users that look to be non-system - that is, those that have a home directory
    in /home/, given the directory actually exists. Better heuristics welcome.
    """
    if not users: users = pwd.getpwall()
    return [p.pw_name for p in users if p.pw_dir.startswith(home_dir) and os.path.exists(p.pw_dir)]

def get_all_other_users(existing_users, users=None):
    if not users: users = pwd.getpwall()
    return [p.pw_name for p in users if p.pw_name not in existing_users]

def change_password(name):
    password = UniversalInput(i, o, message="New password", charmap="password", name="User&pw app password input").activate()
    if password is None:
        return None
    result = passwd(name, password)
    if result[0] == True:
        Printer("Change successful", i, o, 3)
        return True
    else:
        logger.warning("Password change failed, output: {}".format(result[1:]))
        Printer("Password change failed! Info available in the logs, can send a bug report", i, o, 3)
        return False

def user_menu(name):
    info = pwd.getpwnam(name)
    mc = [["Name: {}".format(name)],
          ["UID: {}".format(info.pw_uid)],
          ["GID: {}".format(info.pw_gid)],
          ["Home: {}".format(info.pw_dir)],
          ["Shell: {}".format(info.pw_shell)],
          ["Change password", lambda x=name: change_password(x)]]
    Menu(mc, i, o, name="User&pw app user menu for {}".format(name)).activate()

def list_users():
    users = pwd.getpwall()
    # First, all users
    useful_users = ["root"]+get_nonroot_nonsystem_users(users=users)
    mc = [[user, lambda x=user: user_menu(x)] for user in useful_users]
    # Then, add all the system users
    other_users = get_all_other_users(useful_users, users=users)
    mc += [["System: {}".format(user), lambda x=user: user_menu(x)] for user in other_users]
    Menu(mc, i, o, name="User&pw app user list menu").activate()

def callback():
    mc = [["List users", list_users]]
    Menu(mc, i, o, name="User&pw app main menu").activate()
