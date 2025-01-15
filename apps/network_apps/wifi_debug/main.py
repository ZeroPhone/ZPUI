menu_name = "WiFi repair"

from time import sleep

from ui import LoadingBar, PrettyPrinter as Printer, TextReader, Listbox, DialogBox
from zpui_lib.helpers import setup_logger

from libs import dmesg, dkms_debug
from libs.rpi import vcgencmd, rpiinfo, config as rpi_config

import sdio_debug

logger = setup_logger(__name__, "debug")

try:
    import kmodpy
except:
    kmodpy = None
    logger.exception("Kmodpy module not found!")

i = None
o = None

dkms_fail_text = """DKMS fail - driver not installed! Run:
   apt install --reinstall esp8089-dkms
to fix the problem (sorry, we can't do that automatically yet)."""

otp_fail_text = """Your Pi has an OTP fault!
Visit bit.ly/pi_bad_otp for more info.
Press LEFT to pick your hardware."""

lowlevel_mmc_text = """Low-level MMC errors!
Either your ZP was rebooted (for now, that results in ESP failing), or the ESP itself is faulty.
If a reboot does not fix the situation, consider replacing the ESP with a different version."""


def get_hw_version(li):
    if rpiinfo.is_pi_zero():
       if rpiinfo.is_pi_zero_w():
           return "zerow"
       else:
           return "zero"
    else:
        with li.paused:
            if vcgencmd.otp_problem_detected(vcgencmd.otp_dump()):
                TextReader(otp_fail_text, i, o, h_scroll=False).activate()
            else:
                Printer("Hardware detect failed! Pick your hardware:", i, o, 5)
            lc = [["Pi Zero", "zero"], ["Pi Zero W", "zerow"], ["Other", "other"]]
            choice = Listbox(lc, i, o, name="WiFi repair - hw revision picker").activate()
        return choice

def check_esp8089_dkms(li):
    logger.debug("Checking DKMS")
    li.message = "Checking DKMS"
    info = dkms_debug.get_dkms_status_info()
    logger.debug(info)
    if not dkms_debug.dkms_driver_is_installed("esp8089", dkms_info=info):
        logger.debug("DKMS driver not found!")
        with li.paused:
            TextReader(dkms_fail_text, i, o, h_scroll=False).activate()
        return True
    logger.debug("DKMS driver was found!")
    return False

def check_esp8089_module(li):
    li.message = "Checking module"
    logger.debug("Checking ESP8089 module")
    sleep(1)
    modules = dict(kmodpy.kmod.Kmod().list())
    logger.debug(modules)
    if "esp8089" not in modules:
        logger.debug("ESP8089 module not loaded")
        li.message = "Loading module"
        try:
            kmodpy.kmod.Kmod().modprobe("esp8089")
        except kmodpy.kmod.KmodError as e:
            logger.exception("Error while loading module!")
            message = e.message.strip()
            logger.error(message)
            if message == 'Module already loaded':
                logger.error("That's weird, ESP8089 module detect fail but modprobe says it's already loaded!")
            elif message == "Could not modprobe 'esp8089'":
                logger.info("ESP not accessible?")
            else:
                logger.error("Unknown error!")
        except:
            logger.exception("Yet-unknown ESP8089 module loading error")
            with li.paused:
                Printer("Unknown ESP8089 module loading error!", i, o)
        else:
            with li.paused:
                Printer("Loaded ESP8089 module!", i, o)
            return True, True
    else:
        logger.debug("ESP8089 module already loaded")
    return False, False

def check_brcmfmac_module(li, try_load=False):
    li.message = "Checking module"
    logger.debug("Checking brcmfmac module")
    sleep(1)
    modules = dict(kmodpy.kmod.Kmod().list())
    logger.debug(modules)
    if "brcmfmac" not in modules:
        # brcmfmac not loaded, let's try and load it
        logger.debug("brcmfmac module not loaded")
        li.message = "Loading module"
        try:
            kmodpy.kmod.Kmod().modprobe("brcmfmac")
        except kmodpy.kmod.KmodError as e:
            logger.exception("Error while loading module!")
            message = e.message.strip()
            logger.error(message)
            if message == 'Module already loaded':
                logger.error("That's weird, brcmfmac module detect fail but modprobe says it's already loaded!")
            elif message == "Could not modprobe 'brcmfmac'":
                logger.info("SDIO not accessible?")
            else:
                logger.error("Unknown error!")
        except:
            logger.exception("Yet-unknown brcmfmac module loading error")
            with li.paused:
                Printer("Unknown brcmfmac module loading error!", i, o)
        else:
            with li.paused:
                Printer("Loaded brcmfmac module!", i, o)
            return True, True
    else:
        # brcmfmac loaded, let's try and reload it
        if try_load:
            # we already tried, seems like it hasn't unloaded and we couldn't/didn't load it
            # so, let's not repeat ourselves
            logger.debug("brcmfmac module still loaded?")
            return False, False
        unloaded = False
        li.message = "Unloading module"
        try:
            kmodpy.kmod.Kmod().rmmod("brcmfmac")
        except kmodpy.kmod.KmodError as e:
            logger.exception("Error while unloading module!")
            message = e.message.strip()
            logger.error(message)
        except:
            logger.exception("Yet-unknown brcmfmac module unloading error")
            with li.paused:
                Printer("Unknown brcmfmac module unloading error!", i, o)
        else:
            with li.paused:
                Printer("Unloaded brcmfmac module! Will try and load it back now", i, o)
                unloaded = True
        # A single call to itself to try and reload the module
        # Maybe ESP8089 could benefit from that too?
        # Will try to load regardless of whether it was actually unloaded
        problem_found, problem_fixed = check_brcmfmac_module(li, try_load=True)
        if not problem_found or problem_fixed:
            with li.paused:
                if unloaded:
                    logger.debug("Couldn't load the module back!")
                    Printer("Couldn't load the module back!", i, o)
                else:
                    logger.debug("Couldn't load the module!")
                    Printer("Couldn't load the module!", i, o)
            return False, False
        elif problem_fixed:
            return True, True
    return False, False

def check_dmesg(li):
    li.message = "Checking dmesg"
    sleep(0.5)
    logger.info("Parsing dmesg output")
    dmesg_msgs = dmesg.get_dmesg()
    if sdio_debug.check_lowlevel_mmc_errors(dmesg_msgs):
        logger.exception("Low-level MMC errors! Either ESP is not compatible or a reboot is needed")
        with li.paused:
            TextReader(lowlevel_mmc_text, i, o, h_scroll=False).activate()
        # problem found
        return True
    # problem not found
    return False

def check_zero_config_txt(li):
    li.message = "Checking config.txt"
    sleep(0.5)
    logger.info("Checking config.txt (Zero)")
    entries = rpi_config.get_config()
    miniuart_was_on = rpi_config.make_sure_is_commented_out("dtoverlay", "pi3-miniuart-bt", entries, reason="Auto-commented out by Fix WiFi app")
    sdio_was_off = rpi_config.make_sure_is_uncommented("dtoverlay", "sdio,poll_once=off", entries, reason="Auto-uncommented by Fix WiFi app")
    if sdio_was_off or miniuart_was_on:
        if sdio_was_off:
            logger.info("Found a problem: SDIO was off")
        if miniuart_was_on:
            logger.info("Found a problem: MiniUART BT overlay was on")
        rpi_config.write_config(rpi_config.recreate_config(entries))
        return True
    return False

def check_zerow_config_txt(li):
    li.message = "Checking config.txt"
    sleep(0.5)
    logger.info("Checking config.txt (Zero W)")
    entries = rpi_config.get_config()
    sdio_was_on = rpi_config.make_sure_is_commented_out("dtoverlay", "sdio,poll_once=off", entries, reason="Auto-commented out by Fix WiFi app")
    miniuart_was_off = rpi_config.make_sure_is_uncommented("dtoverlay", "pi3-miniuart-bt", entries, reason="Auto-uncommented by Fix WiFi app")
    if sdio_was_on or miniuart_was_off:
        if sdio_was_on:
            logger.info("Found a problem: SDIO was on")
        if miniuart_was_off:
            logger.info("Found a problem: MiniUART BT overlay was off")
        rpi_config.write_config(rpi_config.recreate_config(entries))
        return True
    return False

def init_app(input, output):
    global i, o
    i = input
    o = output

def callback():
    problem_found = False
    problem_fixed = False
    logger.debug("App launched")
    li = LoadingBar(i, o, message="Detecting hardware")
    li.run_in_background()
    sleep(1) # Showing the message a little bit
    hw_version = get_hw_version(li)
    if not hw_version:
        return False # User pressed LEFT in Listbox
    # DKMS check
    # if hardware is undetected, do we need to check it?
    # ask the user.
    hw_wrong_but_check_esp = False
    if hw_version == "other":
        hw_wrong_but_check_esp = DialogBox("yn", i, o, message="Using ESP8266?").activate()
    # This deals with ESP8266 problems
    if hw_version == "zero" or hw_wrong_but_check_esp:
        #check dkms module
        problem_found = check_esp8089_dkms(li)
        #check esp8089 module
        if not problem_found:
            if kmodpy:
                problem_found, problem_fixed = check_esp8089_module(li)
            else:
                logger.debug("kmodpy not available, not checking the esp8089 module")
        # Check dmesg
        if not problem_found:
            problem_found = check_dmesg(li)
        # Check config.txt
        if not problem_found:
            problem_found = problem_fixed = check_zero_config_txt(li)
    elif hw_version == "zerow":
        # Check brcmfmac module
        problem_found, problem_fixed = check_brcmfmac_module(li)
        # Check config.txt
        if not problem_found:
            problem_found = problem_fixed = check_zerow_config_txt(li)
    li.stop()
    if problem_found:
        if problem_fixed:
            Printer("Fixed some problems!", i, o)
        else:
            Printer("Couldn't fix problems!", i, o)
    else:
        Printer("No problems found!", i, o)
