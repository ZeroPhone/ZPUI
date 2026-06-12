# -*- coding: utf-8 -*-

#TODO: export into ui.funcs?
import string
printable_characters = set(string.printable)

from zpui_lib.ui import Menu, TextReader, replace_filter_ascii as rfa
from zpui_lib.helpers import setup_logger, get_platform

i = None
o = None
zpui = None
git_if = None

logger = setup_logger(__name__, "warning")

about_text = """ZPUI (beta)

A user interface for small non-touch displays.
Developed for ZeroPhone, works on many platforms.
Docs: zpui.rtfd.org
Github: https://github.com/ZeroPhone/ZPUI
License: Apache 2.0, with MIT components.

- git {}, {} branch
- device: {}
- platform:
{}

- config:
{}

"""

def about():
    mc = [["About ZPUI", about_zpui],
          ["Config info", about_config],
          ["Contributors", about_contributors],
          ["Supporters", about_supporters]]
    Menu(mc, i, o, name="Settings-About menu").activate()

def about_zpui():
    try:
        branch = git_if.get_current_branch()
        head = git_if.get_head_for_branch(branch)[:7]
    except:
        logger.exception("Can't get git information!")
        branch = "unknown"
        head = "unknown"
    try:
        platform_text = "\n".join(get_platform())
    except:
        logger.exception("Can't get platform information!")
        platform_text = "UNKNOWN"
    device = getattr(zpui, "device", "none")
    raw_config = zpui.raw_config
    text = about_text.format(head, branch, device, platform_text, zpui.raw_config)
    TextReader(text, i, o, name="About ZPUI TextReader", h_scroll=False).activate()

def about_config():
    text = """Device: {}

    Parsed config:
    {}

    Derived input config:
    {}

    Derived output config:
    {}

    Raw_config:
    {}"""
    device = getattr(zpui, "device", "none")
    text = text.format(device, zpui.loaded_config, zpui.input_config, zpui.output_config, zpui.raw_config)
    TextReader(text, i, o, name="About ZPUI TextReader", h_scroll=False).activate()


def about_contributors():
    with open("CONTRIBUTORS.md", 'r') as f:
        contributors_md = f.read()
    lines = contributors_md.split('\n')[2:]
    contributor_names = "\n".join([rfa(line[3:]) for line in lines])
    text = "ZPUI contributors:\n\n"+contributor_names
    TextReader(text, i, o, name="About contributors TextReader").activate()

def about_supporters():
    with open("SUPPORTERS.md", 'r') as f:
        supporters_md = f.read()
    lines = supporters_md.split('\n')[2:]
    supporter_names = "\n".join([rfa(line[3:]) for line in lines])
    text = "ZeroPhone supporters:\n\n"+supporter_names
    TextReader(text, i, o, name="About supporters TextReader").activate()
