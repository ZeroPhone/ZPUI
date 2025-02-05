

from helpers import setup_logger

menu_name = "Phone"

from subprocess import call as os_call
from time import sleep
import traceback

from ui import Refresher, Menu, Printer, PrettyPrinter, DialogBox
from ui.experimental import NumberKeypadInputLayer
from helpers import BackgroundRunner, ExitHelper

from phone import Phone, Modem, ATError


logger = setup_logger(__name__, "warning")

i = None
o = None
init = None
phone = None

def answer():
    #No context switching as for now, so all we can do is
    #answer call is there's an active one
    try:
        phone.answer()
    except ATError:
        pass

def hangup():
    try:
        phone.hangup()
    except ATError:
        pass

def phone_status():
    data = []
    status = phone.get_status()
    callerid = {}
    if status["state"] != "idle":
        callerid = phone.get_caller_id()
    for key, value in status.items():
        if value:
            data.append("{}: {}".format(key, value))
    for key, value in callerid.items():
        data.append("{}: {}".format(key, value))
    return data

def call(number):
    Printer("Calling {}".format(number), i, o, 0)
    try:
        phone.call(number)
    except ATError as e:
        PrettyPrinter("Calling fail! "+repr(e), i, o, 0)
    logger.error("Function stopped executing")

def call_view():
    keymap = {"KEY_ANSWER":[call, "value"]}
    NumberKeypadInputLayer(i, o, "Call number", keymap, name="Phone call layer").activate()

def status_refresher():
    Refresher(phone_status, i, o).activate()


def init_hardware():
    try:
        global phone
        phone = Phone()
        modem = Modem()
        phone.attach_modem(modem)
    except:
        deinit_hardware()
        raise

def deinit_hardware():
    phone.detach_modem()

def wait_for_connection():
    eh = ExitHelper(i).start()
    while eh.do_run() and init.running and not init.failed:
        sleep(1)
    eh.stop()

def check_modem_connection():
    if init.running:
        return False
    elif init.finished:
        return True
    elif init.failed:
        raise Exception("Modem connection failed!")
    else:
        raise Exception("Phone app init runner is in invalid state! (never ran?)")

def init_app(input, output):
    global i, o, init
    i = input; o = output
    i.set_maskable_callback("KEY_ANSWER", answer)
    i.set_nonmaskable_callback("KEY_HANGUP", hangup)
    try:
        #This not good enough - either make the systemctl library system-wide or add more checks
        os_call(["systemctl", "stop", "serial-getty@ttyAMA0.service"])
    except Exception as e:
        logger.exception(e)
    init = BackgroundRunner(init_hardware)
    init.run()

def offer_retry(counter):
    do_reactivate = DialogBox("ync", i, o, message="Retry?").activate()
    if do_reactivate:
        PrettyPrinter("Connecting, try {}...".format(counter), i, o, 0)
        init.reset()
        init.run()
        wait_for_connection()
        callback(counter)

def callback(counter=0):
    try:
        counter += 1
        status = check_modem_connection()
    except:
        if counter < 3:
            PrettyPrinter("Modem connection failed =(", i, o)
            offer_retry(counter)
        else:
            PrettyPrinter("Modem connection failed 3 times", i, o, 1)
    else:
        if not status:
            PrettyPrinter("Connecting...", None, o, 0)
            wait_for_connection()
            callback(counter)
        else:
            contents = [["Status", status_refresher],
                        ["Call", call_view]]
            Menu(contents, i, o).activate()
