menu_name = "Hardware setup"

import os
import sys
import signal
import traceback
from time import sleep

from ui import Menu, PrettyPrinter as Printer, DialogBox, LoadingIndicator, PathPicker, Listbox, ProgressBar, PurposeOverlay
from helpers import setup_logger, read_or_create_config, local_path_gen, write_config, save_config_gen
from actions import FirstBootAction

import smbus
import gpio
import zerophone_hw
sys.excepthook = sys.__excepthook__
gpio.log.setLevel(gpio.logging.INFO)

from mtkdownload import MTKDownloadProcess, collect_fw_folders

hw_version = zerophone_hw.hw_version
local_path = local_path_gen(__name__)
logger = setup_logger(__name__, "warning")
default_gsm_fw_path = "/lib/firmware/"
default_config = '{"mtkdownload_path":"mtkdownload", "gsm_fw_path":"/lib/firmware/"}'
config_path = local_path("config.json")
config = read_or_create_config(config_path, default_config, menu_name+" app")
save_config = save_config_gen(config_path)

i = None
o = None
context = None

versions = {"gamma":"Gamma", "delta":"Delta", "delta-b":"Delta-B"}
unknown_version_str = "Unknown version"
yet_unknown_version_str = "Yet unknown version"

def set_context(c):
    global context
    context = c
    c.register_firstboot_action(FirstBootAction("set_hardware_version", lambda:hw_version_ui(add_purpose=True), depends=None, not_on_emulator=True))

def hw_version_ui(add_purpose=False):
    def get_contents():
       if hw_version.version_unknown():
           version_str = unknown_version_str
       else:
           version = versions.get(hw_version.string(), yet_unknown_version_str)
           version_str = "Version: {}".format(version)
       menu_contents = [
          [version_str],
          ["Change version", set_hw_version]]
       return menu_contents
    m = Menu([], i, o, contents_hook=get_contents, name="ZP hardware version menu")
    if add_purpose:
        m.apply(PurposeOverlay(purpose="Pick ZP HW version"))
    m.activate()

def set_hw_version(offer_zpui_restart=True):
    lbc = sorted([list(reversed(x)) for x in versions.items()])
    choice = Listbox(lbc, i, o, name="ZP hardware version choose listbox").activate()
    if choice:
        try:
            result = hw_version.set_version(choice)
        except:
            logger.exception("Exception while setting hardware version")
            result = False
        if result:
            Printer("Success!", i, o)
            if offer_zpui_restart:
                needs_restart = DialogBox('yn', i, o, message="Restart ZPUI?").activate()
                if needs_restart:
                    os.kill(os.getpid(), signal.SIGTERM)
        else:
            Printer("Failed to set the version =( Please send a bugreport", i, o, 7)
        return result

def change_settings():
    menu_contents = [
      ["Set mtkdownload path", set_mtkdownload_path],
      ["Set firmware path", set_sim_firmware_path, set_default_sim_firmware_path]]
    Menu(menu_contents, i, o, "ZP hardware setup settings menu").activate()

def set_default_sim_firmware_path():
    choice = DialogBox("yn", i, o, name="Hardware setup app default SIM firmware path confirmation", message="Set default FW path?").activate()
    if choice:
        config["gsm_fw_path"] = default_gsm_fw_path
        save_config(config)
        return True
    return False

def set_sim_firmware_path():
    key = "gsm_fw_path"
    default_path = config.get(key, default_gsm_fw_path)
    path = PathPicker(default_path, i, o, dirs_only=True, name="Hardware setup app SIM firmware path picker").activate()
    if path:
        config[key] = path
        save_config(config)
        return True
    return False

def set_mtkdownload_path():
    key = "mtkdownload_path"
    default_path = config[key] if os.path.isabs(config[key]) else "/"
    path = PathPicker(default_path, i, o, name="Hardware setup app mtkdownload path picker").activate()
    if path:
        config[key] = path
        save_config(config)
        return True
    return False

def get_gsm_reset_gpio():
    hw_revs = [["Gamma", "gamma"], ["Delta/Delta-B", "delta"]]
    gpios = {"gamma":502, "delta":496}
    assert(all([hwr[1] in gpios.keys() for hwr in hw_revs])) # check after editing
    hwr = Listbox(hw_revs, i, o, name="Hardware setup app GSM FW picker").activate()
    if not hwr:
        return None
    if hwr == "delta":
        # Enable UARTs
        gpio.setup(500, gpio.OUT)
        gpio.set(500, False)
    gp = gpios[hwr]
    return gp

def flash_image_ui():
    if not MTKDownloadProcess(None, None, path=config["mtkdownload_path"]).mtkdownload_is_available():
        Printer("mtkdownload not found!", i, o, 5)
        choice = DialogBox("yn", i, o, name="Hardware setup app mtkdownload path confirmation", message="Set mtkdownload path?").activate()
        if choice:
            if set_mtkdownload_path():
                # Running again, now the path should be valid
                flash_image_ui()
            return # No need to continue whether we've recursed or not, exiting
    files = collect_fw_folders(config["gsm_fw_path"])
    lbc = [[os.path.basename(file), file] for file in files]
    if not lbc:
        Printer("No firmware images found!", i, o, 5)
        choice = DialogBox("yn", i, o, name="Hardware setup app mtkdownload path confirmation", message="Alternative FW path?").activate()
        if choice:
            if set_sim_firmware_path():
                # Running again, now there should be some firmware
                flash_image_ui()
            return
    choice = Listbox(lbc, i, o, name="Hardware setup app GSM FW picker").activate()
    # A ProgressBar for the flashing specifically
    pb = ProgressBar(i, o, message="Flashing the modem")
    # A LoadingIndicator for everything else
    li = LoadingIndicator(i, o, message="Waiting for modem")
    if choice:
        cb = lambda state: process_state(pb, li, state)
        p = MTKDownloadProcess("/dev/ttyAMA0", choice, callback=cb, path=config["mtkdownload_path"])
        gp = get_gsm_reset_gpio()
        if not gp:
            return
        def reset():
            gpio.setup(gp, gpio.OUT)
            gpio.set(gp, False)
            sleep(0.1)
            gpio.set(gp, True)
        e = None
        try:
            p.write_image(reset_cb=reset)
        except Exception as e:
            e = traceback.format_exc()
        state = p.get_state()
        if state["state"] == "failed" or e:
            choice = DialogBox("yn", i, o, message="Send bugreport?").activate()
            if choice:
                br = BugReport("mtkdownload_flash_fail.zip")
                if e:
                    br.add_text(json.dumps(e), "mtkdownload_exception.json")
                br.add_text(json.dumps(p.dump_info()), "mtkdownload_psinfo.json")
                result = br.send_or_store("/boot/", logger=logger)
                if result[0]:
                    logger.info("Report sent to {}".format(result[1]))
                else:
                    logger.info("Report stored in {}".format(result[1]))

last_state = None

def process_state(pb, li, state):
    # filtering repeated status to avoid wasting CPU power
    global last_state
    if state == last_state:
        return
    last_state = state
    # actually processing the status
    cs = state["state"]
    if cs == "flashing":
        progress = state["progress"]
        li.pause()
        pb.background_if_inactive()
        if pb.progress != progress:
            pb.progress = progress
    elif cs in ["started", "processing", "not_started"]:
        li.background_if_inactive()
        pb.pause()
        if cs == "started":
            li.message = "Waiting for modem"
        elif cs == "processing":
            li.message = "Erasing flash"
        elif cs == "not_started":
            li.message = "Not started (?)"
    elif cs in ["failed", "finished"]:
        pb.stop()
        li.stop()
        if cs == "failed":
            Printer("Failed to flash!", i, o, 5)
        else:
            Printer("Finished!", i, o, 5)
    else:
        logger.warning("Unrecognized status: {} (full: {})".format(cs, state))

def init_app(input, output):
    global main_menu, callback, i, o
    i = input; o = output

def callback():
    main_menu_contents = [
      ["Hardware version", hw_version_ui],
      ["Flash GSM modem", flash_image_ui],
      ["Settings", change_settings]]
    Menu(main_menu_contents, i, o, "ZP hardware setup menu").activate()
