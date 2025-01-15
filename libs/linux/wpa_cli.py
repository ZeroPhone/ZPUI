from subprocess import check_output, CalledProcessError
from ast import literal_eval
from time import sleep

from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "warning")

current_interface = None

#wpa_cli related functions and objects
def wpa_cli_command(*command):
    run = ["wpa_cli"]
    if current_interface:
        run += ["-i"+current_interface]
    try:
        output = check_output(run + list(command))
        if isinstance(output, bytes): output = output.decode("ascii")
        return output
    except CalledProcessError as e:
        output = e.output
        if isinstance(output, bytes): output = output.decode("ascii")
        raise WPAException(command[0], e.returncode, output=output, args=command[1:])

class WPAException(Exception):
    def __init__(self, command, exit_code, args=None, output=None):
        self.command = command
        self.code = exit_code
        self.args = args
        if args != []:
            message = "'wpa_cli {}' returned {}".format(self.command, self.code)
        else:
            message = "'wpa_cli {} {}' returned {}".format(self.command, ' '.join(args), self.code)
        if output:
            message += "\n Output: {}".format(output)
        super(WPAException, self).__init__(message)

#wpa_cli command wrappers and their helpers

def connect_new_network(network_info):
    #First, looking in the known networks
    conf_networks = list_configured_networks()
    network_found = False
    for network in conf_networks:
        if network_info['ssid'] == network['ssid']:
            network_found = True
            select_network(network['network id'])
            return True
    #Then, if it's an open network, just connecting
    if is_open_network(network_info):
        network_id = add_network()
        logger.info(set_network(network_id, 'ssid', '"'+network_info['ssid']+'"'))
        set_network(network_id, 'key_mgmt', 'NONE')
        select_network(network_id)
        return True
    #Else, there's not enough implemented as for now
    if not network_found:
        logger.warning("Hell, I dunno.")
        return False

def is_open_network(network_info):
    #Might be an approach which doesn't take some things into account
    return not is_wpa_enabled(network_info)

def is_wpa_enabled(network_info):
    flags = parse_network_flags(network_info['flags'])
    wpa_enabled = False
    for flag in flags:
        if flag.startswith('WPA'):
            wpa_enabled = True
    return wpa_enabled

def parse_network_flags(flag_string):
    #Flags go each after another, enclosed in "[]" braces
    flags = [flag.strip('[]') for flag in flag_string.split('][')] #If anybody knows a better way, do commit
    return flags

#wpa_cli commands

def get_interfaces():
    output = process_output(wpa_cli_command("interface"))
    output = output[1:] #First line removed by process_output, second line says "Available interfaces"
    return output

def set_active_interface(interface_name):
    #TODO output check
    global current_interface
    # try to set the module's interface variable, then check status
    # if status check fails, set the variable back to what it was
    # and re-raise the exception
    last_interface = current_interface
    try:
        current_interface = interface_name
        output = process_output(wpa_cli_command("status"))
    except:
        current_interface = last_interface
        raise
    # else: all went well
    #if output == "Connected to interface '{}'".format(interface_name):

def get_current_interface():
    #TODO: check without wireless adapter plugged in
    output = process_output(wpa_cli_command("ifname"))
    return output[0]

def connection_status():
    #TODO: check without wireless adapter plugged in
    parameters = {}
    output = process_output(wpa_cli_command("status"))
    for line in output:
        if '=' not in line:
           continue
        else:
           param, value = line.split('=',1)
           parameters[param] = value
    return parameters

def list_configured_networks():
    #Gives a nice table with first row as header and tab-separated elements, so I'll use process_table function
    output = process_output(wpa_cli_command("list_networks"))
    #As of wpa_supplicant 2.3-1, header elements are ['network id', 'ssid', 'bssid', 'flags']
    networks = process_table(output[0], output[1:])
    return networks

def dict_configured_networks_by_ssid():
    networks = list_configured_networks()
    return {n["ssid"]:n for n in networks}

def dict_configured_networks_by_id():
    networks = list_configured_networks()
    return {n["network id"]:n for n in networks}

def select_network(network_id):
    return ok_fail_command("select_network", str(network_id))

def enable_network(network_id):
    return ok_fail_command("enable_network", str(network_id))

def remove_network(network_id):
    return ok_fail_command("remove_network", str(network_id))

def save_config():
    return ok_fail_command("save_config")

def disable_network(network_id):
    return ok_fail_command("disable_network", str(network_id))

def initiate_scan():
    return ok_fail_command("scan")

def disconnect():
    return ok_fail_command("disconnect")

def reconnect():
    return ok_fail_command("reconnect")

def parse_string_from_cli(ssid):
    return literal_eval("'{}'".format(ssid))

def get_scan_results():
    #Currently I know of no way to know if the scan results got updated since last time scan was initiated
    output = process_output(wpa_cli_command("scan_results"))
    #As of wpa_supplicant 2.3-1, header elements are ['bssid', 'frequency', 'signal level', 'flags', 'ssid']
    networks = process_table(output[0], output[1:])
    # Filtering SSIDs to allow for using Unicode SSIDs
    for network in networks:
        network["ssid"] = parse_string_from_cli(network["ssid"])
    return networks

def add_network():
    return int_fail_command("add_network")

def set_network(network_id, param_name, value):
    if param_name == "ssid":
        value = 'P'+value
    return ok_fail_command("set_network", str(network_id), param_name, value)

def get_network(network_id, param_name):
    output = wpa_cli_command("get_network", str(network_id), param_name)
    value = process_output(output)[0]
    if value.startswith("'") or value.startswith('"'):
        value = literal_eval(value)
    return value


#Helper commands
def ok_fail_command(command_name, *args):
    #Wrapper around commands which return either "OK" or "FAIL"
    #Might fail if the wireless dongle gets unplugged or something
    output = process_output(wpa_cli_command(command_name, *[str(arg) for arg in args]))
    if output[0] == "OK":
        return True
    else:
        raise WPAException(command_name, output[0], args)

def int_fail_command(command_name, *args):
    output = process_output(wpa_cli_command(command_name, *[str(arg) for arg in args]))
    try:
        return int(output[0])
    except:
        raise WPAException(command_name, output[0], args)

def process_table(header, contents):
    #Takes a tab-separated table and returns a list of dicts, each dict representing a row and having column_name:value mappings
    table = []
    #I'm going to split the header to column names and use those for dictionary keys so that there's no need to hard-code values
    column_names = [name.strip(' ') for name in header.split(' / ')]
    for line in contents:
        row = {}
        values = line.split('\t')
        for i, value in enumerate(values):
            column_name = column_names[i]
            row[column_name] = value
        table.append(row)
    return table

def process_output(output):
    #First line of output of wpa_cli (almost?) always says "Selected interface: $INT"
    # but only if the interface is not passed using "wpa_cli -iinterface".
    lines = output.split('\n')
    if not current_interface:
        lines = lines[1:] #First line has the "Selected interface: $INT"
    return [line.strip(' ') for line in lines if line] #Removing all whitespace and not counting empty lines


if __name__ == "__main__":
    print(get_current_interface())
    print(get_interfaces())
    print(list_configured_networks())
    print(connection_status())
    print(initiate_scan())
    for i in range(7):
        sleep(1)
        print(get_scan_results())
    print(initiate_scan())
    print(initiate_scan())
