#!/usr/bin/env python
from evdev import InputDevice, list_devices

devices = [InputDevice(fn) for fn in list_devices()]
print(devices)
for dev in devices:
    print(dev.fn, repr(dev.name), dev.phys, dev.capabilities())
