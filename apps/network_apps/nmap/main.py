menu_name = "Nmap"
i = None
o = None

from functools import wraps
import time
import os, sys

from ui import Menu, PrettyPrinter, Checkbox, NumpadNumberInput, LoadingIndicator, HelpOverlay
from if_info import get_ip_addr, get_network_from_ip, sort_ips

try:
    import nmap
except ImportError:
    nmap = None #So we can give an error if nmap module is missing

#Folder name - to store the saved reports
report_dir = "reports"

#Ports for "unsafe ports" heuristics
#Taken mostly from Wikipedia: https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers
#Can lookup info here, too: http://www.speedguide.net/port.php?port=$PORT_NUM

#Third parameter in list is whether port is selected by default in "port choice" checkbox or not
heuristic_ports = [["SSH,Telnet",          "22,23",                         True],
                   ["HTTP,HTTPS",          "80,443,8080",                   True],
                   ["DNS,TFTP,NTP,RADIUS", "53,69,123,1812",               False],
                   ["SQL,MQTT,cPanel",    "1433,1434,1883,2095,2096,2083",  True],
                   ["Printers",            "9100,515,631,170",              True],
                   ["Routers",             "32764,8089,8291",              True],
                   ["Git/SVN/Bitbucket",   "9418,3690,7990",               False],
                   ["File sharing",        "445,21,944,2049",               True],
                   ["Windows stuff",       "135,445,593",                   True],
                   ["Misc",                "19,502",                       False]]


#Figuring out the path of the app folder - not that simple
current_module_path = os.path.dirname(sys.modules[__name__].__file__)
if report_dir not in os.listdir(current_module_path):
    os.mkdir(os.path.join(current_module_path, report_dir))

report_dir_full_path = os.path.join(current_module_path, report_dir)

#Global storage variables - can be dumped to a file at any time
current_scan = None
current_filename = ""


#Smart scan functions

def smart_scan():
    #First, getting all available interfaces
    networks = []
    interface_data = get_ip_addr()
    for interface_name in interface_data.keys():
        #Autofiltering unsuitable interfaces
        interface_info = interface_data[interface_name]
        state = interface_info["state"]
        ip = interface_info["addr"] if interface_info["addr"] else None
        if state == "up" and ip is not None:
            #Only using interface if it's up and has an IP
            #Automatically filters out localhost
            networks.append( ["{}:{}".format(interface_name, ip), ip] )
    if not networks:
        #No suitable interfaces found after filtering
        PrettyPrinter("No suitable network interfaces found!", i, o, 3)
        return None
    if len(networks) == 1:
        #Only one good interface, using it automatically
        network_ip = networks[0][1]
    else:
        #Allowing user to pick an interface
        network_ip = Listbox(networks, i, o).activate()
        if network_ip is None: #Listbox exited without making a choice
            return None
    network_ip = get_network_from_ip(network_ip)
    chosen_ports = Checkbox(heuristic_ports, i, o, name="NMap: select port types", final_button_name="Run scan").activate()
    if chosen_ports is None: return None
    chosen_port_list = [port_choice for port_choice in chosen_ports if chosen_ports[port_choice] == True]
    port_string = ",".join(chosen_port_list)
    #So the library I'm using is silently failing. I launch the scan from command-line and see:
    #
    #WARNING: Duplicate port number(s) specified.  Are you alert enough to be using Nmap?  Have some coffee or Jolt(tm).
    #
    #Well, thank you, but it's a script and fuck off.
    port_string = ",".join(list(set(port_string.split(","))))
    #De-duplicated and ready to go.
    print(port_string)
    with LoadingIndicator(i, o, message=network_ip):
        nm = nmap.PortScanner()
        nm.scan(network_ip, arguments="-n -p {}".format(port_string))
    print(nm)
    show_quick_scan_results_for_network(network_ip, nm)

#"Arbitrary IP/network scan" functions

class NumpadIPAddressInput(NumpadNumberInput):
    #Making an UI input element with IP address-suitable character mapping
    default_mapping = {"1":"1", "2":"2", "3":"3", "4":"4", "5":"5", "6":"6", "7":"7", "8":"8", "9":"9", "0":"0", "*":".*", "#":"/"}

def cleanup_validate_ip(ip):
    if "/" in ip:
        #Got a netmask, checking it
        parts = ip.split("/")
        #Do we have more than one / in IP?
        if len(parts) != 2:
            raise ValueError("stray / in IP!")
        else:
            ip, netmask = parts
        #Is netmask an integer?
        try:
            netmask = int(netmask, 10)
        except:
            raise ValueError("netmask is not an integer")
        #Is netmask between 0 and 32?
        if netmask < 0 or netmask > 32:
            raise ValueError("netmask out of IPv4 range")
    else:
        #Got no netmask
        netmask = None
    octets = ip.split(".")
    #Do we have exactly 4 octets?
    if len(octets) != 4:
        raise ValueError("expected x.x.x.x format")
    #A list to for invalid octets - to show them all in one error message
    invalid_octets = []
    #A list for new octets - in case any are fixed
    new_octets = []
    for octet in octets:
        if octet == "":
            #Can have an empty octet, which counts as 0
            #Allows to write "127...1" (sorry, no "127.1" yet)
            octet = "0"
            new_octets.append(octet)
            continue
        elif octet == "*":
            #Nothing to check
            new_octets.append(octet)
            continue
        #Is each octet a proper integer?
        try:
            octet = int(octet, 10)
        except:
            invalid_octets.append(octet)
            continue #One octet invalid but need to go to the next one
        #Is each octet in proper range?
        if octet < 0 or octet > 255:
            invalid_octets.append(octet)
        else:
            new_octets.append(octet)
    if len(invalid_octets) == 1:
        #Just one invalid octet
        raise ValueError("invalid octet: {}".format(invalid_octets[0]))
    elif len(invalid_octets) > 1:
        #Multiple invalid octets
        octet_string = ",".join([str(octet) for octet in invalid_octets])
        raise ValueError("invalid octets: {}".format(octet_string))
    else:
        #No invalid octets, assembling the IP and returning it
        ip = ".".join([str(octet) for octet in new_octets])
        if netmask: ip = ip+"/"+str(netmask)
        return ip

def scan_arbitrary_ip():
    ip = NumpadIPAddressInput(i, o, message="IP to scan:").activate()
    if ip is None: return #Cancelled
    valid_ip = False
    while not valid_ip:
        #Validating the IP in a loop
        try:
            ip = cleanup_validate_ip(ip)
        except ValueError as e:
            #If not valid, giving an opportunity to either fix it or cancel the scan
            PrettyPrinter("Invalid ip: {}! Reason: {}".format(ip, e.message), i, o, 3)
            ip = NumpadIPAddressInput(i, o, message="Fix the IP", value=ip).activate()
            if ip is None: return #Cancelled
            #To the next loop iteration
        else:
            valid_ip = True
    if "/" in ip:
        #Network address with a netmask, interpreting it as a network address and just calling nmap
        quick_scan_network_by_ip(ip)
    elif "*" in ip:
        PrettyPrinter("Wildcards without a netmask are not yet supported by the interface, sorry", i, o, 3)
        return
    else:
        scan_ip(ip)


#"Dump scan to file" functions

def dump_current_scan_to_file():
    if current_scan is not None:
        filename = "{}.xml".format(current_filename)
        filename = filename.replace("/", "-") #For netmasks
        report_path = os.path.join(report_dir_full_path, filename)
        with open(report_path, "w") as f:
            xml = current_scan.get_nmap_last_output()
            f.write(xml)
        print("Saved report {}".format(filename))

def save_restore_global_storage(func):
    """A decorator that restores previous contents of report storage
    once the function that last overwrote it exits."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        global current_scan, current_filename
        __current_scan__ = current_scan
        __current_filename__ = current_filename
        result = func(*args, **kwargs)
        current_scan = __current_scan__
        current_filename = __current_filename__
        return result
    return wrapper


#IP/interface/network scanning functions

def scan_localhost(host = "127.0.0.1"):
    scan_ip(host)

def scan_ip(ip, ports="0-1023"):
    with LoadingIndicator(i, o, message="{}:{}".format(ip, ports)):
        nm = nmap.PortScanner()
        nm.scan(ip, ports)
    show_scan_results_for_ip(ip, nm)

def quick_scan_network_by_ip(ip_on_network):
    if ip_on_network == "None":
        PrettyPrinter("No IP to scan!", i, o, 2)
        return False
    network_ip = get_network_from_ip(ip_on_network)
    with LoadingIndicator(i, o, message=network_ip):
        nm = nmap.PortScanner()
        nm.scan(network_ip, arguments="-sn")
    show_quick_scan_results_for_network(network_ip, nm)


#Different menus

def scan_network_menu():
    #A report to be passed to Menu object
    networks = []
    #External library function that parses "ip addr" output
    interface_data = get_ip_addr()
    for interface_name in interface_data.keys():
        interface_info = interface_data[interface_name]
        state = interface_info["state"]
        ip = interface_info["addr"] if interface_info["addr"] else "None"
        networks.append( ["{}:{}, {}".format(interface_name, state, ip), lambda x=ip: quick_scan_network_by_ip(x)] )
    Menu(networks, i, o).activate()

def ip_info_menu(ip_info):
    ip = ip_info["addresses"]["ipv4"]
    mac = ip_info["addresses"]["mac"] if "mac" in ip_info["addresses"] else "Unknown MAC"
    vendor = ip_info["vendor"][mac] if mac in ip_info["vendor"] else "Unknown vendor"
    menu_contents = [
    ["IP: {}".format(ip)],
    [mac],
    [vendor]]
    if "tcp" in ip_info.keys() and ip_info["tcp"]:
        open_ports = []
        for port_num in ip_info["tcp"].keys():
            port_info = ip_info["tcp"][port_num]
            if port_info["state"] == 'open':
                open_ports.append(["{}:{}".format(port_num, port_info["name"])])
        if open_ports:
            menu_contents.append(["Open ports:"])
            menu_contents += open_ports
        else:
            menu_contents.append(["No open ports found"])
    menu_contents.append(["-Scan ports 0-1023", lambda: scan_ip(ip)])
    Menu(menu_contents, i, o).activate()


#Scan result display functions

@save_restore_global_storage
def show_scan_results_for_ip(ip, ip_results):
    global current_scan, current_filename
    current_scan = ip_results
    current_filename = "ip_{}_{}".format(ip, time.strftime("%Y%m%d-%H%M%S"))
    ip_result = ip_results[ip]
    #Assembling a report we can pass straight to Menu object
    report = []
    #IP, state, hostname
    ip = ip_result["addresses"]["ipv4"]
    report.append([ ["IP: {}, {}".format(ip, ip_result.state())] ])
    report.append([ ["Host: {}".format(ip_result.hostname())] ])
    #Now assemble a list of open ports:
    protocols = ip_result.all_protocols()
    if protocols:
        report.append([["Open ports:"]])
        for protocol in protocols:
            ports = ip_result[protocol].keys()
            ports.sort()
            for port in ports:
                report.append([["  {}:{}".format(protocol, port)]])
    else: #No open ports for any protocol found?
        report.append([["No open ports found"]])
    #Show report
    Menu(report, i, o).activate()

@save_restore_global_storage
def show_quick_scan_results_for_network(net_ip, net_results):
    global current_scan, current_filename
    current_scan = net_results
    current_filename = "net_{}_{}".format(net_ip, time.strftime("%Y%m%d-%H%M%S"))
    net_report = []
    ips = net_results.all_hosts()
    ips = sort_ips(ips)
    for ip in ips:
        result = net_results[ip]
        open_ports_found = "tcp" in result.keys() and result["tcp"]
        if open_ports_found:
            open_port_count = len([port_desc for port_desc in result["tcp"].values() if "state" in port_desc and port_desc["state"] == "open"])
        mac = result["addresses"]["mac"] if "mac" in result["addresses"] else "Unknown MAC"
        if result["vendor"] and mac in result["vendor"].keys():
            info_str = result["vendor"][mac]
        else:
            info_str = mac
        if open_ports_found:
            info_str = "{}P;{}".format(open_port_count, info_str)
        net_report.append([[ip, info_str], lambda x=result: ip_info_menu(x)])
    Menu(net_report, i, o, entry_height=2).activate()


#ZPUI functions

def callback():
    #Check if we have all the software necessary for the app to work
    #If not, show error messages and exit
    if nmap is None:
        PrettyPrinter("nmap Python module not found!", i, o, 3)
        return False
    try:
        nm = nmap.PortScanner()
    except nmap.nmap.PortScannerError:
        PrettyPrinter("nmap not installed!", i, o, 3)
        return False
    #Dump function support
    i.set_maskable_callback("KEY_F6", dump_current_scan_to_file)
    #Constructing and loading app main menu
    menu_contents = [
    ["Smart scan", smart_scan],
    ["Scan a network", scan_network_menu],
    ["Scan arbitrary IP", scan_arbitrary_ip],
    ["Scan localhost", scan_localhost]
    ]
    menu = Menu(menu_contents, i, o)
    help_text = "Press F6 in the scan results menu to save the scan results into a file"
    HelpOverlay(help_text).apply_to(menu)
    menu.activate()
    #Have to remove the dump function callback because once application exits it isn't removed automatically
    i.remove_maskable_callback("KEY_F6")

def init_app(input, output):
    global i, o
    i = input; o = output
