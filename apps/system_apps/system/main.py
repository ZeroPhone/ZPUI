"""
    print(cpu_info())
{'CPU implementer': '0x41', 'Features': 'half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 lpae evtstrm crc32', 'CPU architecture': '7', 'BogoMIPS': '76.80', 'Hardware': 'BCM2709', 'CPU revision': '4', 'CPU part': '0xd03', 'model name': 'ARMv7 Processor rev 4 (v7l)', 'Serial': '00000000f6570ff1', 'processor': '3', 'CPU variant': '0x0', 'Revision': 'a02082'}
    print(is_raspberry_pi())
True
    print(free())
{'UsedBC': 203, 'Used': 672, 'SwapTotal': 99, 'Cached': 431, 'SwapFree': 99, 'Free': 253, 'FreeBC': 722, 'SwapUsed': 0, 'Shared': 17, 'Total': 925, 'Buffers': 38}
    print(linux_info())
(0.0, 0.01, 0.05)
"""

menu_name = "System info"

from subprocess import call
from zpui_lib.ui import Menu, Printer, Refresher, TextReader
from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__)

import sys_info

def uptime_load_data():
    loadavg_string = " ".join([str(number) for number in sys_info.loadavg()])
    uptime_string = sys_info.uptime()
    return [uptime_string, loadavg_string]

def uptime_load_monitor():
    Refresher(uptime_load_data, i, o, 1).activate()

def memory_menu_data():
    memory_info = sys_info.free()
    menu_contents = [
    ["Free {:.2f}MB".format(memory_info["Free"])],
    ["Used {:.2f}MB".format(memory_info["Used"])],
    ["FreeBC {:.2f}MB".format(memory_info["FreeBC"])],
    ["UsedBC {:.2f}MB".format(memory_info["UsedBC"])],
    ["Total {:.2f}MB".format(memory_info["Total"])],
    ["Swap {:.2f}MB".format(memory_info["SwapTotal"])],
    ["SwapUsed {:.2f}MB".format(memory_info["SwapUsed"])],
    ["SwapFree {:.2f}MB".format(memory_info["SwapFree"])],
    ["Cached {:.2f}MB".format(memory_info["Cached"])],
    ["Shared {:.2f}MB".format(memory_info["Shared"])],
    ["Buffers {:.2f}MB".format(memory_info["Buffers"])]]
    return menu_contents

def show_memory():
    Menu([], i, o, contents_hook=memory_menu_data, name="system app memory view menu").activate()

def show_linux_info():
    linux_info = sys_info.linux_info()
    menu_contents = [
        [["Hostname:", linux_info.get("hostname", "Unknown")]],
        [["Kernel version:", linux_info.get("k_release", "Unknown")]],
        [["Architecture:", linux_info.get("machine", "Unknown")]],
    ]
    if "distribution" in linux_info:
        menu_contents.append([["Distribution:", " ".join(linux_info["distribution"])]])
    try:
        release_info = sys_info.os_release()
    except:
        logger.exception("os release data fetch fail!")
    else:
        for key, value in release_info.items():
            name = key.lower().capitalize().replace("_", " ")
            menu_contents.append([ [name, value], lambda x=name, y=value: TextReader(f"{x}: {y}", i, o, name="system info app os-release value reader").activate()])
    Menu(menu_contents, i, o, entry_height=2, name="system app linux info menu").activate()

i = None
o = None

def callback():
    menu_contents = [
    ["Uptime&load", uptime_load_monitor],
    #["CPU", show_cpu],
    ["Memory", show_memory],
    ["Linux info", show_linux_info]
    #["Processes", show_processes]
    ]

    #if detect_raspberry:
    #    menu.contents.append("Raspberry Pi", rpi_menu)
    Menu(menu_contents, i, o, name="System menu").activate()
