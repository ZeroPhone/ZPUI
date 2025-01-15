#!/usr/bin/env python
from evdev import InputDevice, list_devices, categorize, ecodes
from time import sleep
import threading

def listen_for_events(dev):
    for event in dev.read_loop():
        #if event.type == ecodes.EV_KEY:
        print (dev.name, ":  ", str(categorize(event)))

devices = [InputDevice(fn) for fn in list_devices()]
print(devices)
for dev in devices:
    print(dev.name, " - ", dev.fn)
    thread = threading.Thread(target=listen_for_events, args=(dev,))
    thread.daemon = True
    thread.start()

while True:
    sleep(1)
