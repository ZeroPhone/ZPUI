menu_name = "Wireless"

from time import sleep, time
from threading import Thread, Event
from traceback import format_exc

from libs.linux import wpa_cli
from helpers import setup_logger
from actions import FirstBootAction as FBA
from libs.linux.wpa_monitor import WpaMonitor
from ui import Menu, PrettyPrinter as Printer, MenuExitException, UniversalInput, \
               Refresher, DialogBox, ellipsize, Entry, LoadingBar, SpinnerOverlay

import net_ui
import read_conf_data

from pyric import pyw

i = None
o = None
context = None
# wpa-cli-based monitor
monitor = None
# "enable temp-disabled networks" thread reference
etdn_thread = None
# cache created from wpa_cli "list_networks" call
network_cache = None
# last interface used in the app
last_interface = None
# current interface used in the app
current_interface = None
# callback used by WiFi wizard menu to get the connection status
wifi_connect_status_cb = None
# global to keep the connection status
wifi_connect_last_status = None


# a global for NetworkMenu currently active
# (global so that we can refresh it once new scan results come)
net_menu = None
# a global for SpinnerOverlay applied to the menu
# so that we can make it active/inactive when scan is started/finished
net_spinner = None

logger = setup_logger(__name__, "info")

interval_between_scans_in_wizard = 10 # seconds
connect_timeout = 10 # seconds
wizard_scan_delay = 10

class NetMenu(Menu):
    """ Menu to show currently available networks """
    view_mixin = net_ui.NetworkMenuRenderingMixin

def get_scan_results_contents():
    network_menu_contents = []
    networks = wpa_cli.get_scan_results()
    for network in networks:
        if network["ssid"] == '':
            ui_ssid = '[Hidden]'
        else:
            ui_ssid = network["ssid"]
        network_cache = wpa_cli.list_configured_networks()
        network_names = [n["ssid"] for n in network_cache]
        network_is_known = network["ssid"] in network_names
        network_is_secured = False if wpa_cli.is_open_network(network) else True
        network["known"] = network_is_known
        network["secured"] = network_is_secured
        cb = lambda x=network: network_info_menu(x)
        network_menu_contents.append(Entry(ui_ssid, cb=cb, \
                                           network_secured=network_is_secured, \
                                           network_known=network_is_known
                                           ))
    return network_menu_contents

def show_scan_results(activate_spinner=False):
    # The activate_spinner flag is because, when try_scan is called,
    # the scan_started event happens before we can open the net menu,
    # so we need to workaround that and set the spinner state manually.
    # After the first manual set, as long as the menu is open, all
    # the other events are processed correctly.
    global net_menu, net_spinner
    net_menu = NetMenu([], i, o, name="Wireless network menu", \
                       contents_hook=get_scan_results_contents)
    net_spinner = SpinnerOverlay()
    net_spinner.apply_to(net_menu)
    if activate_spinner:
        net_spinner.set_state(net_menu, True)
    net_menu.activate()

def get_network_info_menu_contents(network_info):
    # checking that the network is still known
    kni = None
    network_cache = wpa_cli.dict_configured_networks_by_ssid()
    network_is_known = network_info["ssid"] in network_cache
    if network_is_known:
        kni = network_cache[network_info["ssid"]]
    if kni:
        network_status = kni["flags"] if kni["flags"] else "[ENABLED]"
        id = kni["network id"]
        network_info_contents = [
          ["Connect ({})".format(network_status), lambda x=network_info: connect_to_network(x)],
          ["Enable", lambda x=id: enable_network(x)],
          ["Disable", lambda x=id: disable_network(x)],
          ["Select", lambda x=id: select_network(x)],
          ["Remove", lambda x=id: remove_network(x)],
          ["Edit password", lambda x=id: edit_password(x)],
        ]
    else:
        network_info_contents = [
          ["Connect", lambda x=network_info: connect_to_network(x)]
        ]
    network_info_contents += [
      ["BSSID", lambda x=network_info['bssid']: Printer(x, i, o, 5, skippable=True)],
      ["Frequency", lambda x=network_info['frequency']: Printer(x, i, o, 5, skippable=True)],
      ["Open" if wpa_cli.is_open_network(network_info) else "Secured", lambda x=network_info['flags']: Printer(x, i, o, 5, skippable=True)]
    ]
    return network_info_contents

def network_info_menu(network_info):
    gmc = lambda: get_network_info_menu_contents(network_info)
    Menu([], i, o, "Wireless network info menu", contents_hook=gmc,
         catch_exit=False).activate()

def connect_to_network(network_info):
    #First, looking in the known networks
    configured_networks = wpa_cli.list_configured_networks()
    known = False  # flag that avoids going through the whole "enter password"
                   # thing if the network is known
    for network in configured_networks:
        if network_info['ssid'] == network['ssid']:
            Printer(network_info['ssid'] + " known, connecting", i, o, 1)
            wpa_cli.enable_network(network['network id'])
            wpa_cli.save_config()
            known = True
    #Then, if it's an open network, just connecting
    if not known and wpa_cli.is_open_network(network_info):
        network_id = wpa_cli.add_network()
        Printer("Network is open, adding to known", i, o, 1)
        ssid = network_info['ssid']
        wpa_cli.set_network(network_id, 'ssid', '"{}"'.format(ssid))
        wpa_cli.set_network(network_id, 'key_mgmt', 'NONE')
        Printer("Connecting to "+network_info['ssid'], i, o, 1)
        wpa_cli.enable_network(network_id)
        wpa_cli.save_config()
    #Offering to enter a password
    elif not known:
        input = UniversalInput(i, o, message="Password:", name="WiFi password enter UI element", charmap="password")
        password = input.activate()
        if password is None:
            return False
        network_id = wpa_cli.add_network()
        Printer("Password entered, adding to known", i, o, 1)
        ssid = network_info['ssid']
        wpa_cli.set_network(network_id, 'ssid', '"{}"'.format(ssid))
        wpa_cli.set_network(network_id, 'psk', '"{}"'.format(password))
        Printer("Connecting to "+network_info['ssid'], i, o, 1)
        wpa_cli.enable_network(network_id)
        wpa_cli.save_config()
    #No WPS PIN input possible yet and I cannot yet test WPS button functionality.
    # Setup finished. Now let's check if we're actually connected
    # If we're not, we'll do stuff to try and ensure a connection
    status = wpa_cli.connection_status()
    current_ssid = status.get('ssid', 'None')
    # We might init a LoadingBar, here's a variable to refer to it later
    lb = None
    # we might disable networks, need to re-enable them once we're connected
    disabled_networks = []
    # also, in the "WiFi wizard" menu, we need to return some kind of status
    connect_status = {"connected":False,
                      "reason":None}
    if current_ssid and current_ssid == network_info["ssid"]:
        # We seem to be connected!
        logger.info("right ssid in status instantly, seems like we're connected ")
        connect_status["connected"] = True
        connect_status["reason"] = "instant_connect"
        logger.info("new connect_status: {}".format(connect_status))
    else:
        # Entering the "do something until we're actually connected" phase
        # first - let's start a LoadingBar for user-friendliness
        # and record the time we started connecting, for the same =)
        do_exit = Event()
        lb = LoadingBar(i, o, message="Connecting...", on_left=do_exit.set)
        lb.run_in_background()
        start_time = time()
        # don't want to waste time waiting for scan results
        scan_has_been_initiated = False
        # second - we'll be monitoring events, so that we're a bit more efficient
        # and we don't need to go through a bunch of old events => flush
        monitor.flush_status()
        # third - let's do enable_temp_disabled_networks
        enable_temp_disabled_networks()
        # fourth - let's check if we're currently connected to another network
        # if so - we should disable it
        connected = False
        while not connected and not do_exit.isSet():
          if current_ssid != network_info["ssid"]:
            status = wpa_cli.connection_status()
            current_ssid = status.get('ssid', None)
            # what if a race condition happens?
            # lol
            while current_ssid not in [None, network_info["ssid"]]:
                unwanted_net_id = status.get("id", None)
                unwanted_net_ssid = status.get("ssid", None)
                if unwanted_net_id is not None:
                    logger.info("Disabling unwanted network: {} (id: {})".format(unwanted_net_ssid, unwanted_net_id))
                    wpa_cli.disable_network(unwanted_net_id)
                    disabled_networks.append(unwanted_net_id)
                else:
                    # connected to a network but id is not present in the status?
                    # weird.
                    logger.warning("Network connected but id is not available! Status: {}".format(status))
                    # calling the "disconnect" function
                    # but first, let's check if we're really really not connected yet
                    # we're in a weird place already
                    if try_scan():
                        scan_has_been_initiated = True
                    status = wpa_cli.connection_status()
                    current_ssid = status.get('ssid', None)
                    if current_ssid not in [None, network_info["ssid"]]:
                      try:
                        wpa_cli.disconnect()
                      except:
                        logger.exception("and we can't disconnect from the network, either")
                    else:
                        # all is good, it seems
                        if current_ssid == network_info["ssid"]:
                            connected = True
                            logger.info("ssid is set after 'disconnect', seems like we're connected")
                            connect_status["connected"] = True
                            connect_status["reason"] = "ssid_check_after_disconnect_unknown_id"
                            logger.info("new connect_status: {}".format(connect_status))
                            break
                logger.info("Disconnecting from wrong network {}: trying scan".format(unwanted_net_ssid))
                if try_scan():
                    scan_has_been_initiated = True
                logger.info("Disconnecting from wrong network {}: getting status".format(unwanted_net_ssid))
                status = wpa_cli.connection_status()
                current_ssid = status.get('ssid', None)
          # we might've gotten connected after the "while current_ssid is wrong" loop
          if current_ssid == network_info["ssid"]:
              #connected = True # commented out because sometimes, when pw is wrong,
                                # it will connect for a second and then disconnect
              logger.debug("ssid is set, we *might* be connected (ssid: {}, status: {})".format(current_ssid, status))
          net_status = monitor.pop_status()
          if net_status:
              logger.info("Connecting: received status from monitor: {}".format(net_status))
              code = net_status.get("code", "")
              wrong_pw = False
              if code == "CTRL-EVENT-CONNECTED":
                  net_id = net_status["data"].get("id", None)
                  network_cache = wpa_cli.dict_configured_networks_by_id()
                  if network_cache[str(net_id)]["ssid"] == network_info["ssid"]:
                      # yay!
                      logger.info("received a CONNECTED event, seems like we're connected")
                      connected = True
                      connect_status["connected"] = True
                      connect_status["reason"] = "got_connected_status"
                      logger.info("new connect_status: {}".format(connect_status))
                      break
              elif code == "CTRL-EVENT-DISCONNECTED":
                 reason = net_status["data"].get("reason", None)
                 wanted_bssid = network_info["bssid"]
                 bssid = net_status["data"].get("bssid", None)
                 logger.info(" ".join([reason, bssid, wanted_bssid]))
                 if (bssid and bssid == wanted_bssid) and reason in ["2", "3"]:
                     logger.info("received a DISCONNECTED event with what seems like a 'WRONG PASSWORD' code")
                     wrong_pw = True
              elif code == "CTRL-EVENT-SSID-TEMP-DISABLED":
                 reason = net_status["data"].get("reason", None)
                 wanted_ssid = network_info["ssid"]
                 ssid = net_status["data"].get("ssid", None)
                 logger.info(" ".join([reason, ssid, wanted_ssid]))
                 if (ssid and ssid == wanted_ssid) and reason == "WRONG_KEY":
                     logger.info("received a SSID-TEMP-DISABLED event with what seems like a 'WRONG PASSWORD' reason")
                     wrong_pw = True
              elif code == "CTRL-EVENT-SCAN-RESULTS":
                  status = wpa_cli.connection_status()
                  current_ssid = status.get('ssid', None)
                  if current_ssid is None:
                      # we're not connected to anything
                      available_networks = wpa_cli.get_scan_results()
                      for a_network in available_networks:
                          if a_network["ssid"] == network_info["ssid"]:
                          # desired network is present in the network search results
                          # let's call "wpa_cli reconnect"
                          # in hopes that triggers a connection
                              logger.info("We're not connected but network is present in scan results, calling 'wpa_cli reconnect'")
                              wpa_cli.reconnect()
                              break
                      else:
                          # break didn't trigger - network is no longer there?
                          connect_status["connected"] = False
                          connect_status["reason"] = "network_lost"
                          logger.info("new connect_status: {}".format(connect_status))
                          break
              if wrong_pw:
                  lb.stop()
                  while lb.is_active:
                      sleep(0.1)
                  lb = None
                  logger.info("Wrong password, seems like we're not getting connected!")
                  Printer("Wrong password?", i, o, 3)
                  connect_status["connected"] = False
                  connect_status["reason"] = "wrong_password"
                  logger.info("new connect_status: {}".format(connect_status))
                  break
          # fifth - we should check if the network is still available - that is,
          # can be found in scan results
          # so, let's trigger the scan and wait for the results to come
          # if network is available and we're not connected to anything,
          # we'll receive CTRL-EVENT-SCAN-RESULTS and then do further action
          # in the status processing code above
          if not scan_has_been_initiated:
              # this flag can be set in the "disabling other networks" code
              if try_scan():
                  scan_has_been_initiated = True
          # sixth - we should check if we haven't timeouted yet, by any chance ;-P
          now_time = time()
          if now_time - start_time > connect_timeout:
              lb.stop()
              while lb.is_active:
                  sleep(0.1)
              lb = None
              logger.info("Connection timeout, seems like we're not getting connected!")
              Printer("Connect timeout!", i, o, 3)
              connect_status["connected"] = False
              connect_status["reason"] = "timeout"
              logger.info("new connect_status: {}".format(connect_status))
              break
    if lb:
        # LoadingBar was created, stopping it
        lb.stop()
    # re-enabling all the networks we previously disabled
    for net_id in disabled_networks:
        logger.info("Re-enabling network {} that was disabled during connection".format(net_id))
        wpa_cli.enable_network(net_id)
    if callable(wifi_connect_status_cb):
        wifi_connect_status_cb(connect_status)
    logger.info("end connect_status: {}".format(connect_status))
    raise MenuExitException

def enable_temp_disabled_networks():
    global etdn_thread
    if not etdn_thread:
        etdn_thread = Thread(target=etdn_runner, name="Runner for wpa_cli app's EnableTempDisabledNetworks function")
        etdn_thread.daemon = True
        etdn_thread.start()

def etdn_runner():
    global etdn_thread
    network_cache = wpa_cli.list_configured_networks()
    for network in network_cache:
        if network["flags"] == "[TEMP-DISABLED]":
            logger.warning("Network {} is temporarily disabled, re-enabling".format(network["ssid"]))
            try:
                enable_network(network["network id"], silent=True)
            except Exception as e:
                logger.error(format_exc())
                logger.exception(e)
    etdn_thread = None

def scan(delay = True, silent = False):
    delay = 1 if delay else 0
    try:
        wpa_cli.initiate_scan()
        enable_temp_disabled_networks()
    except wpa_cli.WPAException as e:
        if e.code=="FAIL-BUSY":
            if not silent:
                Printer("Still scanning...", i, o, 1)
        else:
            raise
    else:
        if not silent:
            Printer("Scanning...", i, o, 1)
    finally:
        sleep(delay)

def try_scan():
    """
    Initiates scan, doesn't fail on WPAError: FAIL-BUSY
    Returns True if scan successfully initiated, False on FAIL-BUSY
    Raises all the other exceptions
    """
    try:
        wpa_cli.initiate_scan()
    except wpa_cli.WPAException as e:
        if e.code=="FAIL-BUSY":
            return False
        else:
            raise
    except:
        logger.exception("Tried to scan, failed for some reason")
        raise
    else:
        return True


def reconnect():
    try:
        w_status = wpa_cli.connection_status()
    except:
        return ["wpa_cli fail".center(o.cols)]
    ip = w_status.get('ip_address', None)
    ap = w_status.get('ssid', None)
    if not ap:
        Printer("Not connected!", i, o, 1)
        return False
    net_id = w_status.get('id', None)
    if not net_id:
        logger.error("Current network {} is not in configured network list!".format(ap))
        return False
    disable_network(net_id)
    scan()
    enable_network(net_id)
    return True

def status_refresher_data():
    try:
        w_status = wpa_cli.connection_status()
    except:
        return ["wpa_cli fail".center(o.cols)]
    # This function is written for character displays
    # so, if you're wondering why there are magic numbers and weird formatting,
    # this is why =)
    #Getting data
    state = w_status['wpa_state']
    ip = w_status.get('ip_address', 'None')
    ap = w_status.get('ssid', 'None')

    #Formatting strings for screen width
    if len(ap) > o.cols: #AP doesn't fit on the screen
        ap = ellipsize(ap, o.cols)
    if o.cols >= len(ap) + len("SSID: "):
        ap = "SSID: "+ap
    ip_max_len = 15 #3x4 digits + 3 dots
    if o.cols >= ip_max_len+4: #disambiguation fits on the screen
        ip = "IP: "+ip
    data = [ap.center(o.cols), ip.center(o.cols)]

    #Formatting strings for screen height
    #Additional state info
    if o.rows > 2:
       data.append(("St: "+state).center(o.cols))
    #Button usage tips - we could have 3 rows by now, can we add at least 3 more?
    if o.rows >= 6:
       empty_rows = o.rows-6 #ip, ap, state and two rows we'll add
       for i in range(empty_rows): data.append("") #Padding
       data.append("ENTER: more info".center(o.cols))
       data.append("UP: reconnect".center(o.cols))
       data.append("RIGHT: rescan".center(o.cols))

    return data

def status_monitor():
    keymap = {"KEY_ENTER":wireless_status, "KEY_RIGHT":lambda: scan(False), "KEY_UP":lambda: reconnect()}
    refresher = Refresher(status_refresher_data, i, o, 0.5, keymap, "Wireless monitor")
    refresher.activate()

def get_wireless_status_mc():
    w_status = wpa_cli.connection_status()
    state = w_status['wpa_state']
    status_menu_contents = [[["state:", state]]] # State is an element that's always there.
    # Let's process possible states:
    if state == 'COMPLETED':
        # We have bssid, ssid and key_mgmt at least
        status_menu_contents.append(['SSID: '+w_status['ssid']])
        status_menu_contents.append(['BSSID: '+w_status['bssid']])
        key_mgmt = w_status['key_mgmt']
        status_menu_contents.append([['Security:', key_mgmt]])
        # If we have WPA in key_mgmt, we also have pairwise_cipher and group_cipher set to something other than NONE so we can show them
        if key_mgmt != 'NONE':
            try: # What if?
                group = w_status['group_cipher']
                pairwise = w_status['pairwise_cipher']
                status_menu_contents.append([['Group/Pairwise:', group+"/"+pairwise]])
            except:
                pass
    elif state in ['AUTHENTICATING', 'SCANNING', 'ASSOCIATING']:
        pass #These states don't have much information
    #In any case, we might or might not have IP address info
    status_menu_contents.append([['IP address:',w_status['ip_address'] if 'ip_address' in w_status else 'None']])
    #We also always have WiFi MAC address as 'address'
    status_menu_contents.append(['MAC: '+w_status['address']])
    return status_menu_contents

def wireless_status():
    Menu([], i, o, contents_hook=get_wireless_status_mc, name="Wireless status menu", entry_height=2).activate()

def change_interface():
    menu_contents = []
    interfaces = pyw.winterfaces()
    for interface in interfaces:
        menu_contents.append([interface, lambda x=interface: change_current_interface(x)])
    Menu(menu_contents, i, o, "Interface change menu").activate()

def change_current_interface(interface):
    global current_interface, last_interface
    try:
        wpa_cli.set_active_interface(interface)
    except wpa_cli.WPAException:
        Printer('Failed to change interface', i, o, skippable=True)
    else:
        Printer('Changed to '+interface, i, o, skippable=True)
        restart_monitor(interface=interface)
        current_interface = interface
        last_interface = interface
    finally:
        raise MenuExitException

def save_changes():
    try:
        wpa_cli.save_config()
    except wpa_cli.WPAException:
        Printer('Failed to save changes', i, o, skippable=True)
    else:
        Printer('Saved changes', i, o, skippable=True)

def get_saved_networks_mc():
    global network_cache
    network_cache = wpa_cli.list_configured_networks()
    network_menu_contents = []
    #As of wpa_supplicant 2.3-1, header elements are ['network id', 'ssid', 'bssid', 'flags']
    for num, network in enumerate(network_cache):
        network_menu_contents.append([
          "{0[network id]}: {0[ssid]}".format(network),
          lambda x=num: saved_network_menu(network_cache[x]["network id"])
        ])
    return network_menu_contents

def saved_networks():
    Menu([], i, o, name="Saved network menu",
         contents_hook=get_saved_networks_mc, catch_exit=False).activate()

def get_saved_network_menu_contents(network_id):
    network_cache = wpa_cli.list_configured_networks()
    network_info = None
    for network in network_cache:
        if network_id == network['network id']:
            network_info = network
    if not network_info:
        return None
    bssid = network_info['bssid']
    network_status = network_info["flags"] if network_info["flags"] else "[ENABLED]"
    id = network_id
    network_info_contents = [
      [network_status],
      ["Select", lambda x=id: select_network(x)],
      ["Enable", lambda x=id: enable_network(x)],
      ["Disable", lambda x=id: disable_network(x)],
      ["Remove", lambda x=id: remove_network(x)],
      ["Edit password", lambda x=id: edit_password(x)],
      ["BSSID", lambda x=bssid: Printer(x, i, o, 5, skippable=True)]
    ]
    return network_info_contents

def saved_network_menu(network_id):
    ch = lambda x=network_id: get_saved_network_menu_contents(x)
    def ochf(menu, exception=False):
        if not exception:
            # Returned None - network no longer present
            Printer("Network no longer in the network list! 0_0", None, o, 1)
        menu.deactivate()
    Menu([], i, o, "Wireless network info", contents_hook=ch,
         on_contents_hook_fail=ochf, catch_exit=False).activate()
    # After menu exits, we'll request the status again and update the network list
    network_cache = wpa_cli.list_configured_networks()

def select_network(net_id):
    try:
        wpa_cli.select_network(net_id)
    except wpa_cli.WPAException:
        Printer('Failed to select network', i, o, skippable=True)
    else:
        wpa_cli.save_config()
        Printer('Selected network '+ str(net_id), i, o, skippable=True)

def enable_network(net_id, silent=False):
    try:
        wpa_cli.enable_network(net_id)
    except wpa_cli.WPAException:
        if not silent:
            Printer('Failed to enable network', i, o, skippable=True)
    else:
        wpa_cli.save_config()
        if not silent:
            Printer('Enabled network '+str(net_id), i, o, skippable=True)

def disable_network(net_id):
    try:
        wpa_cli.disable_network(net_id)
    except wpa_cli.WPAException:
        Printer('Failed to disable network', i, o, skippable=True)
    else:
        wpa_cli.save_config()
        Printer('Disabled network '+str(net_id), i, o, skippable=True)

def remove_network(net_id):
    want_to_remove = DialogBox("yn", i, o, message="Remove network?").activate()
    if not want_to_remove:
        return
    try:
        wpa_cli.remove_network(net_id)
    except wpa_cli.WPAException:
        Printer('Failed to remove network', i, o, skippable=True)
    else:
        wpa_cli.save_config()
        Printer('Removed network '+str(net_id), i, o, skippable=True)
        raise MenuExitException

def edit_password(net_id):
    conf_fail = False
    try:
        conf_data = read_conf_data.read_data()
    except:
        conf_data = {}
        conf_fail = True
    ssid = wpa_cli.get_network(net_id, "ssid")
    conf = conf_data.get(ssid, None)
    if not conf:
        if conf_fail:
            Printer("Configuration file can't be read, can't get current password!", i, o)
        else:
            Printer("Network not found in the configuration file, can't get current password!", i, o)
        psk = ""
    else:
        psk = conf.get("psk", "")
        if not psk:
            if conf.get("key_mgmt", None) == "NONE":
                result = DialogBox("yn", i, o, message="Is open, edit?").activate()
                if not result:
                    return
                psk = ""
            else:
                # weird, no psk in file
                # using an empty string for now
                psk = ""
    input = UniversalInput(i, o, value=psk, message="Password:", name="WiFi password enter UI element")
    password = input.activate()
    if password is None:
        return False
    wpa_cli.set_network(net_id, 'psk', '"{}"'.format(password))
    wpa_cli.save_config()
    Printer("Password entered", i, o, 1)

# wpa_monitor control functions

def receive_event(event):
    # Hook for us to react on certain messages
    logger.info("Received event: {}".format(event))
    if event["code"] == "CTRL-EVENT-SCAN-RESULTS":
        if net_spinner and net_menu:
            net_spinner.set_state(net_menu, False)
        if net_menu and net_menu.is_active:
            try:
                net_menu.trigger_contents_hook()
            except:
                logger.exception("NetMenu contents_hook failed for some reason ;-(")
            else:
                if net_menu.in_foreground and net_menu.in_background:
                    net_menu.refresh()
    elif event["code"] == "CTRL-EVENT-SCAN-STARTED":
        if net_spinner and net_menu:
            net_spinner.set_state(net_menu, True)

def restart_monitor(interface=None):
    stop_monitor()
    if not interface:
        interface = current_interface
    start_monitor(interface=interface)

def start_monitor(interface=None):
    global monitor
    if not interface:
        interface = current_interface
    if monitor:
        stop_monitor()
    monitor = WpaMonitor()
    monitor.start(interface=interface, event_cb=receive_event)

def stop_monitor():
    global monitor
    if monitor:
        monitor.stop()
    monitor = None

def wizard_scan_thread(connected):
    sleep_time = 0.1
    while not connected.isSet():
        times_to_sleep = wizard_scan_delay / sleep_time
        try_scan()
        for i in range(int(times_to_sleep)):
            # periodically checking the event to avoid the thread lingering in background for a long time
            if connected.isSet():
                return
            sleep(sleep_time)

def start_scan_thread(event):
    t = Thread(target=wizard_scan_thread, args=(event,))
    t.daemon = True
    t.start()

def wifi_connect_wizard():
    global current_interface, wifi_connect_status_cb
    # picking a wireless interface to go with
    # needed on i.e. RPi3 to avoid the p2p-dev-wlan0 stuff
    # thanks Raspbian developers, you broke a lot of decent WiFi setup tutorials
    # even if by accident =(
    # also needed to support proper multi-interface work for the app
    answer = DialogBox("yn", i, o, message="Connect to WiFi?").activate()
    if not answer:
        Printer("Please connect to WiFi later on so that ZPUI and system can be updated - or add some other connectivity now.", i, o, 3, skippable=True)
        return None
    winterfaces = pyw.winterfaces()
    if not winterfaces:
        Printer("No wireless cards found, can't configure WiFi!", i, o, 3, skippable=True)
        return False
    current_interface = winterfaces[0] # Simple, I know
    # Might add some ZP-specific logic here later, so that
    # i.e. the ESP-12 based WiFi is guaranteed to be the first
    # Testing if we actually can connect
    try:
        wpa_cli.set_active_interface(current_interface)
    except OSError as e:
        if e.errno == 2:
            Printer("wpa_cli not found, exiting", i, o, 3, skippable=True)
        else:
            logger.exception("Exception while using wpa_cli to set active interface to {}".format(current_interface))
        return False
    except wpa_cli.WPAException:
        Printer("Can't find any wireless cards. Do you have wireless cards?", i, o, 3, skippable=True)
        return False
    start_monitor()
    # setting up the status collection callback
    def wifi_connect_status_cb(status):
        global wifi_connect_last_status
        wifi_connect_last_status = status
        print(status)
    connected = Event()
    start_scan_thread(connected)
    show_scan_results(activate_spinner=True)
    connected.set()
    stop_monitor()
    wifi_connect_status_cb = None
    if wifi_connect_last_status:
        return wifi_connect_last_status["connected"]
    return False

def set_context(c):
    global context
    context = c
    context.register_firstboot_action(FBA("connect_to_wifi", wifi_connect_wizard, not_on_emulator=True))

def callback():
    # picking a wireless interface to go with
    # needed on i.e. RPi3 to avoid the p2p-dev-wlan0 stuff
    # thanks Raspbian developers, you broke a lot of decent WiFi setup tutorials
    # even if by accident =(
    # also needed to support proper multi-interface work for the app
    global last_interface, current_interface, wifi_connect_status_cb
    winterfaces = pyw.winterfaces()
    if not winterfaces:
        Printer("No wireless cards found, exiting", i, o, 3, skippable=True)
        return
    if last_interface:
        # last_interface is only set when an interface was explicitly changed
        if last_interface in winterfaces:
            # last interface still present
            current_interface = last_interface
        else:
            # last interface no longer present, clearing it to avoid confusion
            # and picking an interface that actually exists
            last_interface = None
            current_interface = winterfaces[0]
    else:
        current_interface = winterfaces[0] # Simple, I know
        # Might add some ZP-specific logic here later, so that
        # i.e. the ESP-12 based WiFi is guaranteed to be the first
    # clearing the connect status callback that might be left over
    # after the WiFi connect wizard
    wifi_connect_status_cb = None
    def get_contents():
        # A function for main menu to be able to dynamically update
        return [
          ["Status", status_monitor],
          ["Current: {}".format(current_interface), change_interface],
          ["Scan", scan],
          ["Networks", show_scan_results],
          ["Saved networks", saved_networks]
        ]
    # Testing if we actually can connect
    try:
        wpa_cli.set_active_interface(current_interface)
    except OSError as e:
        if e.errno == 2:
            Printer("wpa_cli not found, exiting", i, o, 3, skippable=True)
            return
        else:
            raise e
    except wpa_cli.WPAException:
        Printer("Do you have wireless cards? Is wpa_supplicant running? Exiting", i, o, 3, skippable=True)
        return
    else:
        start_monitor()
        Menu([], i, o, "wpa_cli main menu", contents_hook=get_contents).activate()
        stop_monitor()
