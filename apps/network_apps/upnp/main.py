#Code taken from here: https://habrahabr.ru/post/332812/ and, consequently, from here: https://www.electricmonk.nl/log/2016/07/05/exploring-upnp-with-python/


from zpui_lib.helpers import setup_logger

menu_name = "UPnP/SSDP scan"

from zpui_lib.ui import Menu, Printer, IntegerAdjustInput, PrettyPrinter, TextReader
from zpui_lib.helpers import read_or_create_config, write_config, local_path_gen

from collections import OrderedDict
from traceback import format_exc
from time import sleep
import socket
import sys
import os

logger = setup_logger(__name__, "warning")

#Some globals for us
i = None
o = None

config_filename = "config.json"
default_config = '{"timeout":1,"dst":"239.255.255.250","st":"upnp:rootdevice"}'

local_path = local_path_gen(__name__)
config_path = local_path(config_filename)
config = read_or_create_config(config_path, default_config, menu_name+" app")

def run_scan():
    Printer("Scanning:", i, o, 0)
    msg = [
        'M-SEARCH * HTTP/1.1',
        'Host:{}:1900'.format(config["dst"]),
        'ST:{}'.format(config["st"]),
        'Man:"ssdp:discover"',
        'MX:1',
        '']
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.settimeout(config["timeout"])
    s.sendto(b'\r\n'.join((bytes(m, 'utf8') for m in msg)), (config["dst"], 1900) )

    found_devices = OrderedDict()
    while True:
        try:
            data, addr = s.recvfrom(32*1024)
        except socket.timeout:
            break
        except Exception as e:
            logger.error(format_exc())
            logger.exception(e)
        else:
            ip_str = "{}:{}".format(*addr)
            found_devices[ip_str] = data

    if not found_devices:
        PrettyPrinter("No devices found", i, o, 2)
    else:
        data = [[ip, lambda x=ip, y=d: read_info(x, y)] for ip, d in found_devices.items()]
        Menu(data, i, o).activate()

def read_info(ip_str, data):
    try:
        data = data.decode("ascii")
    except:
        logger.exception("Error decoding data: {}".format(data))
        data = str(data)
    text = "[+] {}\n{}".format(ip_str, data)
    logger.info("Scan data: "+repr(text))
    TextReader(text, i, o, h_scroll=False, name="UPnP/SSDP app {} results TextReader".format(ip_str)).activate()
    # todo: saving scan results

def adjust_timeout():
    global config
    timeout = IntegerAdjustInput(config["timeout"], i, o, message="Socket timeout:").activate()
    if timeout is not None and timeout > 0:
        config["timeout"] = timeout
        write_config(config, config_path)
    elif not timeout > 0:
        PrettyPrinter("Timeout has to be larger than 0!", i, o)

main_menu_contents = [
["Scan", run_scan],
["Change timeout", adjust_timeout]
]

def callback():
    Menu(main_menu_contents, i, o, "UPnP/SSDP app menu").activate()

