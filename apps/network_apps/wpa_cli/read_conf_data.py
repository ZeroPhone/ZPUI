from ast import literal_eval

import wpasupplicantconf

# need to un-hardcode it
wpa_supplicant_conf = "/etc/wpa_supplicant/wpa_supplicant.conf"

def read_data(conf=None):
    if not conf:
        conf = wpa_supplicant_conf
    with open(conf, "r") as f:
        lines = f.readlines()
    c = wpasupplicantconf.WpaSupplicantConf(lines)
    nets = dict(c.networks())
    for net, data in nets.items():
        # Normalizing values a bit - just some of them
        psk = data.get("psk", None)
        if psk:
            data["psk"] = literal_eval(psk)
        disabled = data.get("disabled", False)
        if disabled == "1" or int(disabled):
            data["disabled"] = True
        else:
            data["disabled"] = False
        # Converting from the OrderedDict returned from the wpasupplicantconf library
        data = dict(data.items())
        print(net, data)
        nets[net] = data
    return nets

