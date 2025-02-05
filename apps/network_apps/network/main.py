menu_name = "Interfaces"

i = None
o = None

from ui import Menu, PrettyPrinter as Printer
from if_info import parse_ip_addr

ip_shorthands = {"192.168.":"9_6.",
                 "127.0.0.1":"127..1",
                 "169.254.":"LL."}

def get_ifc_menu_contents(ifc_name):
    ifc_dict = parse_ip_addr()
    ifc_data = ifc_dict.get(ifc_name, {})
    ifd_menu_contents = []
    if not ifc_data:
        ifd_menu_contents.append([["Interface", "not found"], lambda:0])
    else:
        if ifc_data['addr'] is not None:
            ip = ifc_data['addr']
            mask = ifc_data['mask']
        else:
            ip = "None"
            mask = "0"
        if ifc_data['addr'] is not None:
            ip6 = ifc_data['addr6']
            mask6 = ifc_data['mask6']
        else:
            ip6 = "None"
            mask6 = "0"
    if not ifd_menu_contents:
        ip_header = "IP: "
        ip6_header = "IP6: "
        mask_str = "/{}".format(mask)
        mask6_str = "/{}".format(mask6)
        ip_header_str = ip_header + mask_str.rjust(o.cols-len(ip_header)) #Magic to make it beautiful
        ip6_header_str = ip6_header + mask6_str.rjust(o.cols-len(ip6_header))
        ifd_menu_contents = [
        ["state: "+str(ifc_data['state']), lambda: 0],
        [[ip_header_str, ip], lambda: Printer(str(ifc_data['addr']), i, o, 3)],
        [[ip6_header_str, ip6], lambda: Printer(str(ifc_data['addr6']), i, o, 3)],
        ["MAC: "+str(ifc_data['ph_addr']), lambda: Printer(str(ifc_data['ph_addr']), i, o, 3)],
        ]
    return ifd_menu_contents

def show_ifc_data(ifc_name):
    ch = lambda x=ifc_name: get_ifc_menu_contents(x)
    ifd_menu = Menu([], i, o, "{} interface data menu".format(ifc_name), entry_height=2, contents_hook=ch)
    ifd_menu.activate()

ifc_states = {"down":"D", "up":"U", 'unknown':"?"}

def get_if_menu_contents():
    menu_contents = []
    ifc_dict = parse_ip_addr()
    for ifc, ifc_data in ifc_dict.items():
        print(ifc, ifc_data)
        ifc_state = ifc_states.get(ifc_data["state"], "X")
        ifc_name = "{}: {}".format(ifc, ifc_state)
        ip = ifc_data.get("addr", None)
        if ip and ip != "None":
            for part, shortened in ip_shorthands.items():
                if ip.startswith(part):
                    ip = ip.replace(part, shortened)
            ifc_name += ", "+ip
        menu_contents.append([ifc_name, lambda x=ifc: show_ifc_data(x)])
    return menu_contents

def callback():
    Menu([], i, o, "Interface selection menu", contents_hook=get_if_menu_contents).activate()
