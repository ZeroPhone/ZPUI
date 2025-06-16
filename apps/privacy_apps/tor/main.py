menu_name = "Tor control app"

from subprocess import call
from time import sleep

from zpui_lib.ui import Menu, Printer, Refresher
import tor


i = None
o = None

def can_load():
    # the app is old and long untested, sadly. alas. it's been fun
    if not tor.stem:
        return False, "STEM library not installed!"
    if not tor.socks:
        return False, "socks library not installed!"
    return False, "app mothballed until its code is updated"

def toggle_status():
    if tor.tor_is_available():
        call(["systemctl", "stop", "tor.service"])
    else:
        call(["systemctl", "start", "tor.service"])
    sleep(2)

def get_status():
    status_list = []
    enabled = tor.tor_is_available()
    try:
        external_ip = tor.get_external_ip()
    except:
        external_ip = str(None)
    if enabled:
        status_list.append("Tor is enabled")
        bytes_read, bytes_written = tor.get_traffic_info()
        status_list.append("External IP:")
        status_list.append(external_ip)
        status_list.append("Sent: {}B".format(bytes_written))
        status_list.append("Received: {}B".format(bytes_read))
    else:
        status_list.append("Tor is disabled?")
        status_list.append("External IP:")
        status_list.append(external_ip)
    return [s.center(o.cols) for s in status_list]

def status_refresher():
    Printer("Getting Tor status...", i, o, 0, skippable=True)
    Refresher(get_status, i, o, 10).activate()

def check_conn():
    Printer("Getting DuckDuckGo", i, o, 0, skippable=True)
    try:
        response = tor.get_duckduckgo()
    except:
        Printer(["Getting DuckDuckGo", "Failed!"], i, o, 2, skippable=True)
    else:
        if response.status_code == 200:
            Printer(["Getting DuckDuckGo", "Success!"], i, o, 2, skippable=True)
        else:
            Printer(["Getting DuckDuckGo", "HTTP code "+str(response.status_code)], i, o, 2, skippable=True)

def renew_connection():
    Printer("Renewing connection...", i, o, 0, skippable=True)
    try:
        tor.renew_connection()
    except:
        Printer(["Renewing connection", "Failed!"], i, o, 2, skippable=True)
    else:
        Printer(["Renewing connection", "Success!"], i, o, 2, skippable=True)

def show_entry_nodes():
    Refresher(entry_node_info, i, o, 50).activate()

def entry_node_info():
    node_info = []
    node_info_dict = tor.get_entry_ips()
    for node_id in sorted(node_info_dict.keys()):
        node_info.append("{}: {}".format(node_id, node_info_dict[node_id]))
    return node_info


def main_menu_contents():
    #Allows to get a nice menu where labels autoupdate when status changes
    is_available = tor.tor_is_available()
    contents = [
    ["Refresh", lambda: True], #Just invoking any callback from a menu can refresh it
    ["Status: {}".format("enabled" if is_available else "disabled"), status_refresher],
    ["Turn off" if is_available else "Turn on", toggle_status],
    ["See entry nodes", show_entry_nodes],
    ["Renew connection", renew_connection],
    ["Check Tor connection", check_conn]
    ]
    return contents

def callback():
    tor.setup()
    Menu([], i, o, "Tor app menu", contents_hook=main_menu_contents).activate()

