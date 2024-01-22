import subprocess
#Description used for all interfaces
from copy import copy

if_description = {
 
   'state':'down',
   'addr':None,
   'addr6':None,
   'ph_addr':None
}

def parse_params(param_string):
    state = None
    words = param_string.split(" ")
    for index, word in enumerate(words):
        if word == 'state':
            state = words[index+1].lower()
    return {'state':state}

def get_ip_addr():
    interfaces = {}
    current_if = None
    ip_output = subprocess.check_output(['ip', 'addr'])
    ip_output = [line for line in ip_output.split('\n') if line != ""]
    for line in ip_output:
        if line[0].isdigit(): #First line for interface
            num, if_name, params = line.split(':', 2)
            if_name = if_name.strip(" ")
            current_if = if_name
            interfaces[if_name] = copy(if_description)
            param_dict = parse_params(params)
            interfaces[if_name].update(param_dict)
        else: #Lines that continue describing interfaces
            line = line.lstrip()
            if line.startswith('inet '):
                words = line.split(" ")
                interfaces[current_if]['addr'] = words[1]
            if line.startswith('link/ether'):
                words = line.split(" ")
                interfaces[current_if]['ph_addr'] = words[1]
            if line.startswith('inet6'):
                words = line.split(" ")
                interfaces[current_if]['addr6'] = words[1]
    return interfaces

def get_network_from_ip(ip_str):
    ip, mask_len_str = ip_str.split('/')
    mask_len = int(mask_len_str)
    ip_byte_repr_str = ip_to_byte_str(ip)
    net_ip_byte_repr_str = ip_byte_repr_str[:mask_len][::-1].zfill(32)[::-1]
    network_ip = byte_str_to_ip(net_ip_byte_repr_str)
    return "{}/{}".format(network_ip, mask_len_str)

def ip_to_byte_str(ip):
    octets = ip.split('.')
    ip_byte_repr_str = "".join([bin(int(octet))[2:].zfill(8) for octet in octets])
    return ip_byte_repr_str

def byte_str_to_ip(byte_str):
    octets = [str(int(byte_str[i*8:][:8], 2)) for i in range(4)]
    ip = ".".join(octets)
    return ip

def sort_ips(ips):
    #Let's try and sort the IPs by their integer representation
    ip_to_int_repr = {}
    for ip in ips:
        #Converting IP to its integer value
        int_repr = int(ip_to_byte_str(ip), 2)
        #Adding it to a dictionary to preserve integer_ip-to-ip link
        ip_to_int_repr[int_repr] = ip
    #Sorting the integer representations
    int_reprs = ip_to_int_repr.keys()
    int_reprs.sort()
    #Now returning the IPs associated with integer representations - by order of elements the sorted list
    return [ip_to_int_repr[int_repr] for int_repr in int_reprs]

if __name__ == "__main__":
    print(get_ip_addr())
    ip = "192.168.88.153/24"
    network = get_network_from_ip(ip)
    print("IP {} is from network {}".format(ip, network))
