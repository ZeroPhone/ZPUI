menu_name = "Partitions"

import sys, os
from subprocess import Popen, PIPE
import time #Wish I could import some more time...

from ui import Menu, Printer, MenuExitException

import device_info

timeout = 3

pending_umounts = {}

def list_mounts():
    menu_contents = []
    mounts = device_info.get_mounted_partitions()
    for device in mounts:
        mountpoint = mounts[device]
        menu_contents.append([mountpoint, lambda x=mountpoint, y=device: view_mount(x, y)])
    Menu(menu_contents, i, o).activate()

def view_mount(mountpoint, device):
    menu_contents = [
    [["Device:", device]],
    [["Mountpoint:", mountpoint]],
    ["Unmount", lambda x=mountpoint: umount(x)],
    ["Unmount (lazy)", lambda x=mountpoint: umount(x, lazy=True)],
    ["Eject", lambda x=device: eject(x)]]
    Menu(menu_contents, i, o, entry_height=2, catch_exit=False).activate()

def eject(device):
    command = ["eject", device]
    p = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    counter = timeout/0.1
    while p.poll() is None:
        if counter == 0:
           break
        time.sleep(0.1)
        counter -= 1
    print(p.poll())
    if p.poll() is not None:
        code = p.returncode
        if code == 0:
            Printer("Ejected!", i, o)
        else:
            Printer(["Can't eject!", "code {}".format(code)], i, o)
    else:
        Printer("Timeouted", i, o)
    raise MenuExitException

def umount(path, lazy=False):
    global pending_umounts
    command = ["umount"]
    if lazy: command.append("-l")
    command.append(path)
    p = Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    counter = timeout/0.1
    while p.poll() is None:
        if counter == 0:
           break
        time.sleep(0.1)
        counter -= 1
    print(p.poll())
    if p.poll() is not None:
        code = p.returncode
        if code == 0:
            Printer("Unmounted!", i, o)
        else:
            Printer(["Can't unmount!", "code {}".format(code)], i, o)
    else:
        Printer(["Timeouted", "added to pending"], i, o)
        pending_umounts[path] = p
    raise MenuExitException
 
def status_menu():
    pass

callback = None
i = None
o = None

def init_app(input, output):
    global i, o, callback
    i = input; o = output
    menu_contents = [
    #["Partitions", list_partitions],
    ["Mounts", list_mounts]
    #["Drives", list_drives],
    #["Status", status_menu]]
    ]
    callback = Menu(menu_contents, i, o, name="Partitions app main menu").activate

