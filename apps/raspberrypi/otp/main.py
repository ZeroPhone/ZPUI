menu_name = "Pi OTP dump"
i = None
o = None

#from time import sleep
from subprocess import check_output #, CalledProcessError

from ui import Menu, PrettyPrinter as Printer, TextReader
from zpui_lib.helpers import setup_logger, is_emulator, local_path_gen

logger = setup_logger(__name__)
local_path = local_path_gen(__name__)

try:
    import OTPParser as otp
except:
    logger.exception("Cannot load OTPParser!")
    otp = False

url = "https://github.com/CRImier/RaspberryPi/raw/master/OTPParser.py"

vcgencmd = False

def can_load():
    global vcgencmd
    if not otp:
        return False, "OTPParser library was not found / didn't load!"
    if not is_emulator():
        try:
            check_output(["vcgencmd", "otp_dump"])
        except:
            logger.exception("Exception when test running vcgencmd otp_dump!")
            return False, "vcgencmd failure"
        else:
            vcgencmd = True
    else:
        vcgencmd = False # emulator, blindly assuming that it's not a Pi - will supply dummy data instead
    return True

def callback():
    if vcgencmd:
        try:
            output = check_output(["vcgencmd", "otp_dump"])
        except:
            logger.exception("Exception when test running vcgencmd otp_dump!")
            Printer("vcgencmd failed to run", i, o, 2)
            return
    else:
        # loading test data
        Printer("vcgencmd not found; loading test data", i, o, 1)
        with open(local_path("test_otp_zero2w"), 'r') as f:
            output = f.read()
    # parsing output
    if '\r\n' in output:
        output = output.replace('\r\n', '\n')
    lines = filter(None, [line.strip() for line in output.split('\n')])
    Printer("Parsing otp data...", i, o, 0)
    try: # library processing the data internally
        otp.__read_otp_file_inner(lines)
        otp.process_bootmode()
        otp.process_serial()
        otp.process_revision()
    except:
        logger.exception("Exception in otp parsing library!")
        Printer("Failure during otp parsing!", i, o, 2)
        return
    mc = []

    def append(*args): # a quick feature to convert otp library's prints with
        entry = [args[0].lstrip()]
        entry.append(" ".join(map(str, args[1:])))
        mc.append([entry, lambda x=args: read(x)])

    def read(args):
        text = " ".join(args)
        tr = TextReader(text, i, o, h_scroll=False, name="TextReader for OTP values")
        tr.activate()

    # prints from OTPParser rearranged, but otherwise minimally modified
    append('                     Board Type :', 'RPi Model ' + otp.BOARD_TYPES_AS_STRING.get(otp.BOARD['type'], "{} (unknown)".format(bin(int(otp.BOARD["type"], 2))) ) )
    append('                  Serial Number :', otp.get('serial_number', 'hex'))
    append('          Inverse Serial Number :', otp.get('serial_number_inverted', 'hex'))
    append('                            RAM :', otp.MEMORY_SIZES_AS_STRING[otp.BOARD['memory']], "MB")
    append('                   Manufacturer :', otp.MANUFACTURERS_AS_STRING[otp.BOARD['manufacturer']])
    append('                            CPU :', otp.PROCESSORS_AS_STRING[otp.BOARD['processor']])
    append('                    MAC Address :', otp.format_mac())
    append('                Revision Number :', otp.get('revision_number', 'hex'))
    append('              New Revision Flag :', otp.revision('new_flag'))
    append('               Control Register :', otp.get('control', 'hex'), otp.get('control', 'binary'))
    append('        Overvolt Protection Bit :', otp.overclock('overvolt_protection'))
    append('                       Bootmode :', otp.get('bootmode', 'hex'), otp.get('bootmode', 'binary'))
    append('                Bootmode - Copy :', otp.get('bootmode_copy', 'hex'), otp.get('bootmode_copy', 'binary'))
    append('              MPEG2 License Key :', otp.get('codec_key_one', 'hex'))
    append('               VC-1 License Key :', otp.get('codec_key_two', 'hex'))
    append('                 Board Revision :', otp.BOARD_REVISIONS_AS_STRING[otp.BOARD['revision']])
    append('                   Batch Number :', otp.get('batch_number', 'hex'))
    append('JTAG_DEBUG_KEY_PARITY_START_BIT :', otp.pretty_string(otp.control('bits_24-31')))
    append(' VPU_CACHE_KEY_PARITY_START_BIT :', otp.pretty_string(otp.control('bits_16-23')))
    append('               JTAG_DISABLE_BIT :', otp.control('bit_15'))
    append('     JTAG_DISABLE_REDUNDANT_BIT :', otp.control('bit_14'))
    append('          MACROVISION_START_BIT :', otp.control('bit_13'))
    append('MACROVISION_REDUNDANT_START_BIT :', otp.control('bit_11'))
    append('    DECRYPTION_ENABLE_FOR_DEBUG :', otp.control('bit_9'))
    append('                ARM_DISABLE_BIT :', otp.control('bit_7'))
    append('      ARM_DISABLE_REDUNDANT_BIT :', otp.control('bit_6'))
    append('          OSC Frequency 19.2MHz :', otp.bootmode('bit_1'))
    append('            SDIO Pullup Enabled :', otp.bootmode('bit_3'))
    append('               Bootmode (Bit 4) :', otp.bootmode('bit_4'))
    append('               Bootmode (Bit 5) :', otp.bootmode('bit_5'))
    append('               Bootmode (Bit 7) :', otp.bootmode('bit_7'))
    append('                  GPIO Bootmode :', otp.bootmode('bit_19'))
    append('             GPIO Bootmode Bank :', otp.bootmode('bit_20'))
    append('                SD Boot Enabled :', otp.bootmode('bit_21'))
    append('                      Boot Bank :', otp.bootmode('bit_22'))
    append('         Bootmode (eMMC Enable) :', otp.bootmode('bit_25'), '(This is not confirmed but is set on the CM3)')
    append('        USB Device Boot Enabled :', otp.bootmode('bit_28'))
    append('          USB Host Boot Enabled :', otp.bootmode('bit_29'))
    append('    Boot Signing Parity (15-0)  :', otp.pretty_string(otp.boot_signing_parity('bits_0-15')))
    append('    Boot Signing Parity (31-16) :', otp.pretty_string(otp.boot_signing_parity('bits_16-31')))
    append('            Customer Region One :', otp.get('customer_one', 'hex'))
    append('            Customer Region Two :', otp.get('customer_two', 'hex'))
    append('          Customer Region Three :', otp.get('customer_three', 'hex'))
    append('           Customer Region Four :', otp.get('customer_four', 'hex'))
    append('           Customer Region Five :', otp.get('customer_five', 'hex'))
    append('            Customer Region Six :', otp.get('customer_six', 'hex'))
    append('          Customer Region Seven :', otp.get('customer_seven', 'hex'))
    append('          Customer Region Eight :', otp.get('customer_eight', 'hex'))
    append('                  Advanced Boot :', otp.get('advanced_boot', 'hex'), otp.get('advanced_boot', 'binary'))
    append('             ETH_CLK Output Pin :', otp.pretty_string(otp.advanced_boot('bits_0-6'), False))
    append('         ETH_CLK Output Enabled :', otp.advanced_boot('bit_7'))
    append('             LAN_RUN Output Pin :', otp.pretty_string(otp.advanced_boot('bits_8-14'), False))
    append('         LAN_RUN Output Enabled :', otp.advanced_boot('bit_15'))
    append('                USB Hub Timeout :', otp.process_hub_timeout(otp.advanced_boot('bit_24')))
    append('              ETH_CLK Frequency :', otp.process_eth_clk_frequency(otp.advanced_boot('bit_25')))

    m = Menu(mc, i, o, entry_height=2, name="OTP app otp values menu")
    m.activate()
