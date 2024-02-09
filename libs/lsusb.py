#!/usr/bin/env python

from subprocess import check_output

"""

Bus 001 Device 008: ID 239a:d1ed
Bus 001 Device 015: ID 045e:00db Microsoft Corp. Natural Ergonomic Keyboard 4000 V1.0
Bus 001 Device 014: ID 046d:c52f Logitech, Inc. Unifying Receiver
Bus 001 Device 013: ID 0b95:772a ASIX Electronics Corp. AX88772A Fast Ethernet
Bus 001 Device 012: ID 0d8c:0105 C-Media Electronics, Inc. CM108 Audio Controller
Bus 001 Device 011: ID 17e9:0117 DisplayLink 
Bus 001 Device 010: ID 1a40:0201 Terminus Technology Inc. FE 2.1 7-port Hub
Bus 001 Device 016: ID 04d9:1603 Holtek Semiconductor, Inc. Keyboard
Bus 001 Device 003: ID 0424:ec00 Standard Microsystems Corp. SMSC9512/9514 Fast Ethernet Adapter
Bus 001 Device 002: ID 0424:9514 Standard Microsystems Corp. 
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub

"""


def lsusb():
    lsusb_entries = []
    output = check_output(["lsusb"])
    if isinstance(output, bytes): output = output.decode("ascii")
    for line in [line.strip(' ') for line in output.split('\n') if line.strip(' ')]:
        location, description = line.split(':', 1)
        id_str, vid_pid_name = description.strip(' ').split(' ', 1)
        vid_pid = vid_pid_name.split(' ', 1)[0]
        name = vid_pid_name.split(' ', 1)[1] if len(vid_pid_name.split(' ', 1)) > 1 else None
        bus_str, bus, device_str, device = location.split(' ', 3)
        bus = str(int(bus, 10))
        device = str(int(device, 10))
        lsusb_entries.append([bus, device, vid_pid, name])
    return lsusb_entries


if __name__ == "__main__":
    print(lsusb())
