menu_name = "2FA TOTP"

import pyotp

from ui import Menu, PrettyPrinter as Printer, UniversalInput, Canvas, Refresher, DialogBox
from zpui_lib.helpers import read_or_create_config, local_path_gen, save_config_gen

local_path = local_path_gen(__name__)
config_path = local_path("config.json")
default_config = '{"secrets":[]}'
save_config = save_config_gen(config_path)

i = None
o = None
config = None

def init_app(input, output):
    global i, o
    i = input
    o = output

# Showing TOTP entries

def show_totp(name, secret):
    display_func = lambda: render_totp(name, secret)
    r = Refresher(display_func, i, o, 1)
    delete_func = lambda: delete_config_entry(name, secret, r)
    r.set_keymap({"KEY_RIGHT":delete_func})
    r.activate()

def render_totp(name, secret):
    c = Canvas(o)
    totp_font = ("Fixedsys62.ttf", 32)
    try:
        totp_value = pyotp.TOTP(secret).now()
    except TypeError:
        totp_font = ("Fixedsys62.ttf", 16)
        totp_value = "Incorrect\nsecret!"
    c.centered_text(totp_value, font=totp_font)
    left_coord = c.get_centered_text_bounds(name).left
    c.text(name, (left_coord, 5))
    return c.get_image()

# Config management

def add_secret():
    global config
    name = UniversalInput(i, o, message="Name").activate()
    if name is None:
        return
    secret = UniversalInput(i, o, message="Secret").activate()
    if secret is None:
        return
    config["secrets"].append([name, secret])
    save_config(config)

def delete_config_entry(name, secret, r):
    global config
    # Need to match both name and secret to find the right entry that needs to be deleted
    do_delete = DialogBox("yn", i, o, message="Delete \"{}\"?".format(name)).activate()
    if not do_delete:
        return
    try:
        config["secrets"].remove([name, secret])
    except:
        Printer("Could not delete!", i, o)
        raise
    else:
        save_config(config)
        r.deactivate()

# Main menu

def contents_hook():
    contents = [[name, lambda x=name, y=secret: show_totp(x, y)] for name, secret in config["secrets"]]
    contents.append(["Add TOTP...", add_secret])
    return contents

def callback():
    global config
    config = read_or_create_config(config_path, default_config, menu_name)
    Menu([], i, o, "TOTP app main menu", contents_hook=contents_hook).activate()
