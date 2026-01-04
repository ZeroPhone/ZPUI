#!/usr/bin/env python3
import os
import sys
from subprocess import Popen, check_output
from time import sleep
import traceback

from packaging.version import Version

print("TODO warning about raspberry pi i2c enable")
print("TODO i2c bus number config")

#Using I2C = apt-get python3-smbus i2cdetect
##Using serial - python-serial
#Using pifacecad - pip pifacecad
#Using HID - python evdev
#Using GPIO - RPi.GPIO


#Translation of choices to apt-get and pip modules which need to be installed
#Choice names shouldn't be the same in different modules!
"""
preassembled_modules ={
'pifacecad':{'apt-get':['python-pifacecad']},
'adafruit':{'apt-get':['python3-smbus', 'i2c-tools']},
'chinafruit':{'apt-get':['python3-smbus', 'i2c-tools']},
'adafruit':{'apt-get':['python3-smbus', 'i2c-tools']},
}
"""

preassembled_modules ={
'zerophone_og':{'apt-get':['python3-smbus', 'i2c-tools']},
'zpui_bc_v1':{'apt-get':['python3-smbus', 'i2c-tools', 'python-rpi.gpio']},
'zpui_bc_v1_qwiic':{'apt-get':['python3-smbus', 'i2c-tools']},
'emulator':{'apt-get':["python-pip", "python-dev", "build-essential", "python-pygame"], 'pip':["luma.emulator"]},
'waveshare_oled_hat':{'apt-get':['python3-smbus', 'i2c-tools', 'python-rpi.gpio']},
'beepy':{'apt-get':['python3-smbus', 'i2c-tools', 'python3-rpi.gpio', 'python3-evdev']},
'blepis':{'apt-get':['python3-smbus', 'i2c-tools', 'python3-rpi.gpio', 'python3-evdev']},
'colorberry':{'apt-get':['python3-smbus', 'i2c-tools', 'python3-rpi.gpio', 'python3-evdev']},
}

"""
separate_modules ={
'serial':{'apt-get':['python-serial']},
'i2c':{'apt-get':['python3-smbus', 'i2c-tools']},
'hid':{'apt-get':['python-dev'], 'pip':['evdev']},
'rpi_gpio':{'apt-get':['python-rpi.gpio']}
}
"""

"""
#Radio menu translations:
preassembled_module_names ={
"PiFaceCAD":'pifacecad',
"Adafruit I2C LCD&button shield based on MCP23017 (RGB or other bl)":'adafruit',
"\"LCD RGB KEYPAD ForRPi\", based on MCP23017 (with RGB LED)":'chinafruit'
}
"""
preassembled_module_names ={
"Emulator (pygame)":'emulator',
"OG ZeroPhone hardware":'zerophone_og',
"ZPUI businesscard v1 (QWIIC-only)":'zpui_bc_v1_qwiic',
"ZPUI businesscard v1 (Pi GPIO header)":'zpui_bc_v1',
"Waveshare OLED HAT (untested)":'waveshare_oled_hat',
"Beepy":'beepy',
"Blepis":'blepis',
"Colorberry":'colorberry',
}

"""
preassembled_module_confs = {
"zerophone":"{"input":[{"driver":""}]}",
"emulator":"",
'pifacecad':'{"input":[{"driver":"pfcad"}],"output":[{"driver":"pfcad"}]}',
'adafruit':'{"input":[{"driver":"adafruit_plate"}],"output":[{"driver":"adafruit_plate","kwargs":{"chinese":false}}]}',
'chinafruit':'{"input":[{"driver":"adafruit_plate"}],"output":[{"driver":"adafruit_plate"}]}'
}
"""

preassembled_module_confs = {
"zerophone_og":'device: zerophone_og\n',
"emulator":'device: emulator\n',
'zpui_bc_v1_qwiic':"device: zpui_bc_v1_qwiic\n",
'zpui_bc_v1':"device: zpui_bc_v1\n",
'waveshare_oled_hat':"device: waveshare_oled_hat\n",
'beepy':"device: beepy\n",
'blepis':"device: blepis\n",
'colorberry':"device: colorberry\n",
}



def call_interactive(command):
    p = Popen(command, stdout=sys.stdout, stdin=sys.stdin, stderr=sys.stderr)
    while p.poll() is None:
        try:
            sleep(1)
        except KeyboardInterrupt:
            p.terminate()
            break


def uniq(list_to_uniq):
    seen = set()
    return [x for x in list_to_uniq if not (x in seen or seen.add(x))]


def yes_or_no(string, default=False):
    while True:
        answer = input((string+" ").lower()) #Adding whitespace for prompt to look better
        if answer == "":
            return default
        elif answer.startswith('y'):
            return True
        elif answer.startswith('n'):
            return False
        else:
            pass #Looping until a comprehensible answer is given

def radio_choice(strings, prompt="Choose one:"):
    while True:
        for index, string in enumerate(strings):
            print("{} - {}".format(index, string))
        try:
            choice_str = input((prompt+" "))
        except KeyboardInterrupt:
            return None
        try:
            choice = int(choice_str)
        except ValueError:
            print("Choice should be an integer")
        else:
            break
    return choice

def setup():
    print("Hello! I'm glad that you've chosen ZPUI")
    print("Let me help you out with installing necessary Python modules and utilities.")
    print("Feel free to restart this script if you screwed up")

    options = []
    preassembled_module = None
    module_supplied = False

    if len(sys.argv) > 1: # a name supplied
        module = sys.argv[1]
        if module in preassembled_module_confs:
            module_name = module
            preassembled_module = module_name
            options.append(module_name)
            module_supplied = True
        else:
            print("Module {} not found!".format(repr(module)))
            sys.exit(1)
    if not module_supplied: # no module supplied
        #if yes_or_no("Do you use any of pre-assembled I/O modules, such as PiFaceCAD, one of character LCD&button shields or others?"):
        print("Ctrl^C if your module is not found")
        pretty_names = preassembled_module_names.keys()
        answer = radio_choice(pretty_names)
        if answer is not None:
            module_pname = list(pretty_names)[answer]
            module_name = preassembled_module_names[module_pname]
            preassembled_module = module_name
            options.append(module_name)
        else:
            print("You might still be able to use ZPUI! Just, please, configure it manually =D")
            sys.exit(0)
    #. Do open an issue on GitHub, or, alternatively, try GPIO driver if it's based on GPIO")
    """
    if yes_or_no("Do you connect any of your I/O devices by I2C?"):
        options.append('i2c')
    if yes_or_no("Do you connect any of your I/O devices by serial (UART), either hardware or serial over USB?"):
        options.append('serial')
    if yes_or_no("Do you use HID devices, such as keyboards and keypads?"):
        options.append('hid')
    if yes_or_no("Do you use Raspberry Pi GPIO port devices (not I2C or SPI)?"):
        options.append('rpi_gpio')
    """

    #Joining both module dictionaries for convenience
    both_dicts = {}
    both_dicts.update(preassembled_modules)
    #both_dicts.update(separate_modules)

    apt_get = []
    pip = []
    for option in options:
        option_desc = both_dicts[option]
        apt_get_packages = option_desc['apt-get'] if 'apt-get' in option_desc else []
        pip_modules = option_desc['pip'] if 'pip' in option_desc else []
        for package in apt_get_packages:
            apt_get.append(package)
        for module in pip_modules:
            pip.append(module)

    apt_get = uniq(apt_get)
    pip = uniq(pip)


    print(apt_get)
    print(pip)
    if apt_get:
        try:
            call_interactive(['apt', 'update'])
            call_interactive(['apt', '--ignore-missing', 'install'] + apt_get)
        except FileNotFoundError:
            print("#########################################################")
            print("apt not found on system. this is normal if you're not running a Debian flavour distro.")
            print("for the reference, here are the packages it would've had tried installing:")
            print(" ".join(apt_get))
            print("#########################################################")
        except:
            print("#########################################################")
            print("apt install failed. Exception:")
            traceback.print_exc()
            print("#########################################################")

    if pip:
        cmdline = ["pip", "install"]
        output = check_output(["pip", "--version"])
        if isinstance(output, bytes): output = output.decode("utf-8")
        _, ver, _ = output.split(' ', 2)
        if Version(ver) > Version("23.0.0"):
            cmdline.append("--break-system-packages")
        call_interactive(cmdline + pip)

    print("")
    print("-"*30)
    print("")

    if preassembled_module:
        f = open('config.yaml', 'w')
        f.write(preassembled_module_confs[preassembled_module])
        print("Config: ")
        print(preassembled_module_confs[preassembled_module])
        f.close()
        print("Your config.yaml is set. Run 'python main.py' to start the system and check your hardware.")
        if preassembled_module == "emulator":
            # creating flag file indicating that the device's an emulator
            filename = "emulator"
            if not os.path.exists(filename):
                open(filename, 'a').close()
        elif preassembled_module == 'waveshare_oled_hat':
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("If you've resoldered the OLED HAT to use I2C for the screen,")
            print("add a `screen_hw: i2c` line to the config.yaml.")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        elif preassembled_module.startswith('zpui_bc_v1'):
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("If you've soldered the OLED in a rotation that's not North,")
            print("add a `rotate: E` or `rotate: S` or `rotate: W` line to the config.yaml.")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        print("You'll need to change your config.yaml according to I/O devices you're using (refer to the documentation!)")

if __name__ == "__main__":
    setup()
