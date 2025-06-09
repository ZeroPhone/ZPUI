# ZPUI
[![Build Status](https://travis-ci.org/ZeroPhone/ZPUI.svg?branch=master)](https://travis-ci.org/ZeroPhone/ZPUI)
[![codecov](https://codecov.io/gh/ZeroPhone/ZPUI/graph/badge.svg?token=NMNmpNedXq)](https://codecov.io/gh/ZeroPhone/ZPUI)

ZPUI (Zippy UI) is a small-screen Linux control interface and UI framework.
It gives you access to your system at your fingertips, untethered from any SSH or keyboard/display/mouse requirements.
With ZPUI, you can see your IP address, connect to wireless networks (even do password input with arrow keys in a pinch!), run scripts, manage system services,
reboot and power down your system, view and unmount storage partitions, control media volume, and do much more.

ZPUI is perfect for single-board computers, servers, embedded Linux devices, your broken-screen laptop on a shelf,
wearable and pocket-able devices with Linux under the hood, and much more. OpenWRT support incoming, too.
It is written in Python and it supports third-party apps - you can write your own apps for whatever your heart desires!

All you need for ZPUI is a small screen (I2C/SPI/framebuffer, OLED or LCD) and at least five buttons (GPIO/I2C/HID/etc.)
A single I2C interface is enough - you can even use I2C from a HDMI or VGA port for running ZPUI.
[Install ZPUI](http://zpui.readthedocs.org/en/latest/setup.html) onto your Linux device, and it will be there for you
when you need it.

Want to check it out, or do development? You can also run the ZPUI emulator on your Linux desktop - just
[follow the instructions here.](http://zpui.readthedocs.org/en/latest/setup.html#emulator)

Licensed under Apache 2.0 license, with 3rd party components under MIT - see LICENSE and LICENSE-3RD-PARTY for details
ZPUI is based on [pyLCI](http://pylci.rtfd.io), a previous version for character screens.)

[Project documentation](http://zpui.readthedocs.org/en/latest/)

[ZPUI setup](http://zpui.readthedocs.org/en/latest/setup.html) onto your Linux device, and it will be there for you

[ZPUI emulator setup](http://zpui.readthedocs.org/en/latest/setup.html#emulator) (Linux desktop)

[ZeroPhone archive on Hackaday](https://hackaday.io/project/19035)

