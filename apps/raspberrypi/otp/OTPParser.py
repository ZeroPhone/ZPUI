#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Raspberry Pi OTP Dump Parser

 Copyright 2019-2022 Jasmine Iwanek & Dylan Morrison

 Permission is hereby granted, free of charge, to any person obtaining a copy of this
 software and associated documentation files (the "Software"), to deal in the Software
 without restriction, including without limitation the rights to use, copy, modify, merge,
 publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
 to whom the Software is furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in all copies or
 substantial portions of the Software.

 THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
 PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
 FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
 OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 DEALINGS IN THE SOFTWARE.

 Usage
 call either ./OTPParser.py <filename> or vgcencmd otp_dump | OTPParser
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from string import hexdigits
from os import path
import traceback

if (sys.version_info < (2, 6) or (sys.version_info >= (3, 0) and sys.version_info < (3, 3))):
    sys.exit('OTPParser requires Python 2.6 or 3.3 and newer.')

try:
    from future import standard_library
    standard_library.install_aliases()
except ImportError:
    sys.exit('OTPParser requires future!')

try:
    from builtins import dict, int, open, range, str
except ImportError:
    sys.exit("OTPParser requires future! (Cant import 'builtins'")


class TypoError(Exception):
    """TypoError exception."""
    pass


MEMORY_SIZES = {
    '256':       '000',    # 0
    '512':       '001',    # 1
    '1024':      '010',    # 2
    '2048':      '011',    # 3
    '4096':      '100',    # 4
    '8192':      '101',    # 5
    'unknown_6': '110',    # 6
    'unknown_7': '111',    # 7
    '256/512':   'EITHER',
    'unknown':   ''
}
MEMORY_SIZES_AS_STRING = dict((v, k) for k, v in list(MEMORY_SIZES.items()))

MANUFACTURERS = {
    'Sony UK':    '0000',  # 0
    'Egoman':     '0001',  # 1
    'Embest':     '0010',  # 2
    'Sony Japan': '0011',  # 3
    'Embest #2':  '0100',  # 4
    'Stadium':    '0101',  # 5
    'unknown_6':  '0110',  # 6
    'unknown_7':  '0111',  # 7
    'unknown_8':  '1000',  # 8
    'unknown_9':  '1001',  # 9
    'unknown_a':  '1010',  # a
    'unknown_b':  '1011',  # b
    'unknown_c':  '1100',  # c
    'unknown_d':  '1101',  # d
    'unknown_e':  '1110',  # e
    'unknown_f':  '1111',  # f
    'Qisda':      'QISD',  # Correct value unknown
    'unknown':    ''
}
MANUFACTURERS_AS_STRING = dict((v, k) for k, v in list(MANUFACTURERS.items()))

PROCESSORS = {
    'BCM2835':   '0000',  # 0
    'BCM2836':   '0001',  # 1
    'BCM2837':   '0010',  # 2
    'BCM2711':   '0011',  # 3
    'unknown_4': '0100',  # 4
    'unknown_5': '0101',  # 5
    'unknown_6': '0110',  # 6
    'unknown_7': '0111',  # 7
    'unknown_8': '1000',  # 8
    'unknown_9': '1001',  # 9
    'unknown_a': '1010',  # a
    'unknown_b': '1011',  # b
    'unknown_c': '1100',  # c
    'unknown_d': '1101',  # d
    'unknown_e': '1110',  # e
    'unknown_f': '1111',  # f
    'unknown':   ''

}
PROCESSORS_AS_STRING = dict((v, k) for k, v in list(PROCESSORS.items()))

BOARD_TYPES = {
    'A':         '00000000',  # 0
    'B':         '00000001',  # 1
    'A+':        '00000010',  # 2
    'B+':        '00000011',  # 3
    '2B':        '00000100',  # 4
    'Alpha':     '00000101',  # 5
    'CM1':       '00000110',  # 6
    'Unknown_7': '00000111',  # 7 (Not in known use)
    '3B':        '00001000',  # 8
    'Zero':      '00001001',  # 9
    'CM3':       '00001010',  # a
    'Unknown_b': '00001011',  # b (Not in known use)
    'Zero W':    '00001100',  # c
    '3B+':       '00001101',  # d
    '3A+':       '00001110',  # e
    'Internal':  '00001111',  # f
    'CM3+':      '00010000',  # 10
    '4B':        '00010001',  # 11
    'Zero 2 W':  '00010010',  # 12
    'unknown':   ''
}
BOARD_TYPES_AS_STRING = dict((v, k) for k, v in list(BOARD_TYPES.items()))

BOARD_REVISIONS = {
    '1.0':       '0000',
    '1.1':       '0001',
    '1.2':       '0010',
    '1.3':       '0011',
    'unknown_4': '0100',
    'unknown_5': '0101',
    'unknown_6': '0110',
    'unknown_7': '0111',
    'unknown_8': '1000',
    'unknown_9': '1001',
    'unknown_a': '1010',
    'unknown_b': '1011',
    'unknown_c': '1100',
    'unknown_d': '1101',
    'unknown_e': '1110',
    'unknown_f': '1111',
    '2.0':       ' 2.0',  # Correct Value unknown.
    'unknown':   ''
}
BOARD_REVISIONS_AS_STRING = dict((v, k) for k, v in list(BOARD_REVISIONS.items()))

LEGACY_REVISIONS = {
    '00010': {'memory_size': '256', 'manufacturer': 'Egoman',
              'processor': 'BCM2835', 'board_type': 'B', 'board_revision': '1.0'},
    '00011': {'memory_size': '256', 'manufacturer': 'Egoman',
              'processor': 'BCM2835', 'board_type': 'B', 'board_revision': '1.0'},
    '00100': {'memory_size': '256', 'manufacturer': 'Sony UK',
              'processor': 'BCM2835', 'board_type': 'B', 'board_revision': '2.0'},
    '00101': {'memory_size': '256', 'manufacturer': 'Qisda',
              'processor': 'BCM2835', 'board_type': 'B', 'board_revision': '2.0'},
    '00110': {'memory_size': '256', 'manufacturer': 'Egoman',
              'processor': 'BCM2835', 'board_type': 'B', 'board_revision': '2.0'},
    '00111': {'memory_size': '256', 'manufacturer': 'Egoman',
              'processor': 'BCM2835', 'board_type': 'A', 'board_revision': '2.0'},
    '01000': {'memory_size': '256', 'manufacturer': 'Sony UK',
              'processor': 'BCM2835', 'board_type': 'A', 'board_revision': '2.0'},
    '01001': {'memory_size': '256', 'manufacturer': 'Qisda',
              'processor': 'BCM2835', 'board_type': 'A', 'board_revision': '2.0'},
    '01101': {'memory_size': '512', 'manufacturer': 'Egoman',
              'processor': 'BCM2835', 'board_type': 'B', 'board_revision': '2.0'},
    '01110': {'memory_size': '512', 'manufacturer': 'Sony UK',
              'processor': 'BCM2835', 'board_type': 'B', 'board_revision': '2.0'},
    '01111': {'memory_size': '512', 'manufacturer': 'Egoman',
              'processor': 'BCM2835', 'board_type': 'B', 'board_revision': '2.0'},
    '10000': {'memory_size': '512', 'manufacturer': 'Sony UK',
              'processor': 'BCM2835', 'board_type': 'B+', 'board_revision': '1.0'},
    '10001': {'memory_size': '512', 'manufacturer': 'Sony UK',
              'processor': 'BCM2835', 'board_type': 'CM1', 'board_revision': '1.0'},
    '10010': {'memory_size': '512', 'manufacturer': 'Sony UK',
              'processor': 'BCM2835', 'board_type': 'A+', 'board_revision': '1.1'},
    '10011': {'memory_size': '512', 'manufacturer': 'Embest',
              'processor': 'BCM2835', 'board_type': 'B+', 'board_revision': '1.2'},
    '10100': {'memory_size': '512', 'manufacturer': 'Embest',
              'processor': 'BCM2835', 'board_type': 'CM1', 'board_revision': '1.0'},
    '10101': {'memory_size': '256/512', 'manufacturer': 'Embest',
              'processor': 'BCM2835', 'board_type': 'A+', 'board_revision': '1.1'},
    'default': {'memory_size': 'unknown', 'manufacturer': 'unknown',
                'processor': 'unknown', 'board_type': 'unknown', 'board_revision': 'unknown'}
}

REGIONS = {
    'unknown_8':               8,
    'unknown_9':               9,
    'unknown_10':             10,
    'unknown_11':             11,
    'unknown_12':             12,
    'unknown_13':             13,
    'unknown_14':             14,
    'unknown_15':             15,
    'control':                16,  # Control Register
    'bootmode':               17,  # BootMode Register
    'bootmode_copy':          18,  # Backup copy of BootMode Register
    'boot_sign_key_1':        19,  # OTP_BOOT_SIGNING_KEY Always ffffffff unless on baremetal read
    'boot_sign_key_2':        20,  # OTP_BOOT_SIGNING_KEY Always ffffffff unless on baremetal read
    'boot_sign_key_3':        21,  # OTP_BOOT_SIGNING_KEY Always ffffffff unless on baremetal read
    'boot_sign_key_4':        22,  # OTP_BOOT_SIGNING_KEY Always ffffffff unless on baremetal read
    'boot_sign_key_1_copy':   23,  # OTP_BOOT_SIGNING_KEY_REDUNDANT Always ffffffff unless on baremetal read
    'boot_sign_key_1_copy':   24,  # OTP_BOOT_SIGNING_KEY_REDUNDANT Always ffffffff unless on baremetal read
    'boot_sign_key_1_copy':   25,  # OTP_BOOT_SIGNING_KEY_REDUNDANT Always ffffffff unless on baremetal read
    'boot_sign_key_1_copy':   26,  # OTP_BOOT_SIGNING_KEY_REDUNDANT Always ffffffff unless on baremetal read
    'boot_signing_parity':    27,  # Boot Signing Parity
    'serial_number':          28,  # Serial Number
    'serial_number_inverted': 29,  # Serial Number (Bitflipped)
    'revision_number':        30,  # Revision Number
    'batch_number':           31,  # Batch Number
    'overclock':              32,  # Overclock Register
    'board_rev_extended':     33,  # Extended Board Revision
    'unknown_34':             34,
    'unknown_35':             35,
    'customer_one':           36,  # Customer OTP Region #1
    'customer_two':           37,  # Customer OTP Region #2
    'customer_three':         38,  # Customer OTP Region #3
    'customer_four':          39,  # Customer OTP Region #4
    'customer_five':          40,  # Customer OTP Region #5
    'customer_six':           41,  # Customer OTP Region #6
    'customer_seven':         42,  # Customer OTP Region #7
    'customer_eight':         43,  # Customer OTP Region #8
    'unknown_44':             44,
    'codec_key_one':          45,  # Codec License Key #1 (MPEG2)
    'codec_key_two':          46,  # Codec License Key #2 (WVC-1)
    'cm4_signed_boot_one':    47,  # Reserved for signed-boot on Compute Module 4
    'cm4_signed_boot_two':    48,  # Reserved for signed-boot on Compute Module 4
    'cm4_signed_boot_three':  49,  # Reserved for signed-boot on Compute Module 4
    'cm4_signed_boot_four':   50,  # Reserved for signed-boot on Compute Module 4
    'cm4_signed_boot_five':   51,  # Reserved for signed-boot on Compute Module 4
    'cm4_signed_boot_six':    52,  # Reserved for signed-boot on Compute Module 4
    'cm4_signed_boot_seven':  53,  # Reserved for signed-boot on Compute Module 4
    'cm4_signed_boot_eight':  54,  # Reserved for signed-boot on Compute Module 4
    'cm4_signed_boot_nine':   55,  # Reserved for signed-boot on Compute Module 4
    'unknown_56':             56,
    'unknown_57':             57,
    'unknown_58':             58,
    'unknown_59':             59,
    'unknown_60':             60,
    'unknown_61':             61,
    'unknown_62':             62,
    'unknown_63':             63,
    'mac_address_two':        64,  # MAC Address (Second part)
    'mac_address_one':        65,  # MAC Address (First part)
    'advanced_boot':          66,  # Advanced Boot Register
}

BOARD = {
    'memory':        '000',
    'manufacturer': '0000',
    'processor':    '0000',
    'type':     '00000000',
    'revision':     '0000'
}

DATA = {}


def is_hex(string):
    """Check if the string is hexidecimal.
    Credit to eumiro, stackoverflow:
    https://stackoverflow.com/questions/11592261/check-if-a-string-is-hexadecimal
    """
    hex_digits = set(hexdigits)
    # if string is long, then it is faster to check against a set
    return all(c in hex_digits for c in string)


def control(name):
    """Handler for region 16."""
    indices = {
        'bits_0-5':   (26, 32),  # Unknown/Unused
        'bit_6':      (25, 26),  # OTP_ARM_DISABLE_REDUNDANT_BITXXX
        'bit_7':      (24, 25),  # OTP_ARM_DISABLE_BITXXX
        'bit_8':      (23, 24),  # Unknown/Unused
        'bit_9':      (22, 23),  # OTP_DECRYPTION_ENABLE_FOR_DEBUGXXX
        'bit_10':     (21, 22),  # Unknown/Unused
        'bit_11':     (20, 21),  # OTP_MACROVISION_REDUNDANT_START_BITXXX
        'bit_12':     (19, 20),  # Unknown/Unused
        'bit_13':     (18, 19),  # OTP_MACROVISION_START_BITXXX
        'bit_14':     (17, 18),  # OTP_JTAG_DISABLE_REDUNDANT_BITXXX
        'bit_15':     (16, 17),  # OTP_JTAG_DISABLE_BITXXX
        'bits_16-23': (8, 16),   # OTP_VPU_CACHE_KEY_PARITY_START_BIT (Seen: 0x28)
        'bits_24-31': (0, 8),    # OTP_JTAG_DEBUG_KEY_PARITY_START_BIT (Seen: 0x24 & 0x64)
    }[name]
    __control = get('control', 'binary')
    return __control[indices[0]: indices[1]]


def bootmode(name):
    """Handler for region 17."""
    indices = {
        'bit_0':      (31, 32),  # Unknown (Gordon hinted the Pi wouldn't boot with this set)
        'bit_1':      (30, 31),  # Sets the oscillator frequency to 19.2MHz
        'bit_2':      (29, 30),  # Unknown (Gordon hinted the Pi wouldn't boot with this set)
        'bit_3':      (28, 29),  # Enables pull ups on the SDIO pins
        'bit_4':      (27, 28),  # Set on PI4B
        'bit_5':      (26, 27),  # Set on Pi4B
        'bit_6':      (25, 26),  # Unknown/Unused
        'bit_7':      (24, 25),  # Set on PI4B
        'bits_8-18':  (13, 24),  # Unknown/Unused
        'bit_19':     (12, 13),  # Enables GPIO bootmode
        'bit_20':     (11, 12),  # Sets the bank to check for GPIO bootmode
        'bit_21':     (10, 11),  # Enables booting from SD card
        'bit_22':     (9, 10),   # Sets the bank to boot from (That's what Gordon said, Unclear)
        'bits_23-24': (7, 9),    # Unknown/Unused
        'bit_25':     (6, 7),    # Unknown (Is set on the Compute Module 3)
        'bits_26-27': (4, 6),    # Unknown/Unused
        'bit_28':     (3, 4),    # Enables USB device booting
        'bit_29':     (2, 3),    # Enables USB host booting (Ethernet and Mass Storage)
        'bits_31-30': (0, 2)     # Unknown/Unused
    }[name]
    __bootmode = get('bootmode', 'binary')
    return __bootmode[indices[0]: indices[1]]


def boot_signing_parity(name):
    """Handler for region 27."""
    indices = {
        'bits_0-15':  (16, 32),  # Data seen here
        'bits_16-31': (0, 16),
    }[name]
    __boot_signing_parity = get('boot_signing_parity', 'binary')
    return __boot_signing_parity[indices[0]: indices[1]]


def revision(name):
    """Handler for region 30."""
    indices = {
        'overvoltage':           (0, 1),    # Overvoltage Bit
        'otp_program':           (1, 2),    # OTP Program Bit
        'otp_read':              (2, 3),    # OTP Read Bit
        'bits_26-28':            (3, 6),    # Unused
        'warranty':              (6, 7),    # Warranty Bit
        'bit_24':                (7, 8),    # Unused
        'new_flag':              (8, 9),    # If set, this board uses the new versioning scheme
        'memory_size':           (9, 12),   # Amount of RAM the board has
        'manufacturer':          (12, 16),  # Manufacturer of the board
        'processor':             (16, 20),  # Installed Processor
        'board_type':            (20, 28),  # Model of the board
        'board_revision':        (28, 32),  # Revision of the board
        'legacy_board_revision': (27, 32)   # Region used to store the legacy revision
    }[name]
    __revision = get('revision_number', 'binary')
    return __revision[indices[0]: indices[1]]


def overclock(name):
    """Handler for region 32."""
    indices = {
        'overvolt_protection': (31, 32),  # Overvolt protection bit
        'bits_1-31':           (0, 31)    # Unknown/Unused
    }[name]
    __overclock = get('overclock', 'binary')
    return __overclock[indices[0]: indices[1]]


def advanced_boot(name):
    """Handler for region 66."""
    indices = {
        'bits_0-6':   (25, 32),  # GPIO for ETH_CLK output pin
        'bit_7':      (24, 25),  # Enable ETH_CLK output pin
        'bits_8-14':  (17, 24),  # GPIO for LAN_RUN output pin
        'bit_15':     (16, 17),  # Enable LAN_RUN output pin
        'bits_16-23': (8, 16),   # Unknown/Unused
        'bit_24':     (7, 8),    # Extend USB HUB timeout parameter
        'bit_25':     (6, 7),    # ETH_CLK Frequency (0 = 25MHz, 1 = 24MHz)
        'bits_26-31': (0, 6)     # Unknown/Unused
    }[name]
    __advanced_boot = get('advanced_boot', 'binary')
    return __advanced_boot[indices[0]: indices[1]]


def process_bootmode():
    """Process bootmode, Check against the backup."""
    bootmode_primary = get('bootmode', 'binary')
    bootmode_copy = get('bootmode_copy', 'binary')
    if bootmode_primary != bootmode_copy:
        print('Bootmode fields are not the same, this is a bad thing!')


def process_serial():
    """Process Serial, Check against Inverse Serial."""
    serial = get('serial_number', 'hex')
    inverse_serial = get('serial_number_inverted', 'hex')
    try:
        if (int(serial, 16) ^ int(inverse_serial, 16)) != int('0xffffffff', 16):
            print('Serial failed checksum!')
    except TypeError:
        sys.exit('Serial number format invalid!')


def process_revision():
    """Process Revision, Handle depending on wether it's old or new style."""
    flag = revision('new_flag')
    if flag == '0':
        generate_info_legacy(revision('legacy_board_revision'))
    elif flag == '1':
        generate_info(revision('memory_size'),
                      revision('manufacturer'),
                      revision('processor'),
                      revision('board_type'),
                      revision('board_revision'))


def format_mac():
    """Format MAC Address in a human readable fashion."""
    mac_part_1 = get('mac_address_one', 'raw')
    mac_part_2 = get('mac_address_two', 'raw')
    if not mac_part_1 == '00000000':
        mac = mac_part_1 + mac_part_2
        return ':'.join(mac[i:i+2] for i in range(0, 12, 2))
    return 'None'


def process_hub_timeout(bit):
    """Return the HUB timeout."""
    if bit == '1':
        return '5 Seconds'
    return '2 Seconds'


def process_eth_clk_frequency(bit):
    """Return the ETH_CLK frequency."""
    if bit == '1':
        return '24MHz'
    return '25MHz'


def generate_info_legacy(bits):
    """Generate information for legacy board revision."""
    if bits in list(LEGACY_REVISIONS.keys()):
        input_dict = LEGACY_REVISIONS[bits]
    else:
        input_dict = LEGACY_REVISIONS['default']
    generate_info(MEMORY_SIZES[input_dict['memory_size']],
                  MANUFACTURERS[input_dict['manufacturer']],
                  PROCESSORS[input_dict['processor']],
                  BOARD_TYPES[input_dict['board_type']],
                  BOARD_REVISIONS[input_dict['board_revision']])


def generate_info(memory_size_in, manufacturer_in, processor_in, board_type_in, board_revision_in):
    """Generate information from board revision."""
    BOARD['memory'] = memory_size_in
    BOARD['manufacturer'] = manufacturer_in
    BOARD['processor'] = processor_in
    BOARD['type'] = board_type_in
    BOARD['revision'] = board_revision_in


def get(loc, specifier='raw'):
    """Get data from specified OTP region.
    Specifier determines whether it is returned 'raw', in 'binary', in 'octal', or in 'hex'idecimal.
    """
    region = REGIONS[loc]
    if specifier == 'raw':
        return DATA[region]
    elif specifier == 'binary':
        return format(int(DATA[region], 16), '032b')
    elif specifier == 'hex':
        return format(int(DATA[region], 16), '#010x')
    elif specifier == 'octal':
        # TODO: Ask jas for more details on what she wants the octal output to look like.
        return format(int(DATA[region], 16), '#018o')
    else:
        raise ValueError('Invalid Flag.')


def pretty_string(value, do_binary=True):
    """Return a pretty OTP entry."""
    try:
        intval = int(value, 2)
        hexval = format(int(intval), '#04x')
        return '' + str(intval) + ' (' + hexval + ') ' + (value if (do_binary) else '')
    except ValueError:
        sys.exit('Failed to make the string pretty!')


def read_otp_file():
    """Read OTP from specified file."""
    if len(sys.argv) > 1:  # We're given an argument on the command line
        if path.isfile(sys.argv[1]):
            with open(sys.argv[1], 'r') as otp_file:
                __read_otp_file_inner(otp_file)
        else:
            sys.exit('Unable to open file.')
    else:  # Use stdin instead.
        print("Reading OTP values from stdin")
        __read_otp_file_inner(sys.stdin)


def __read_otp_file_inner(myfile):
    """Inner part of OTP file reader."""
    for line in myfile:
        try:
            if "Command not registered" in line:
                raise TypoError
            try:
                region = int(line.split(':', 1)[0])
            except ValueError:
                sys.exit("Invalid OTP Dump (invalid region number '" + line.split(':', 1)[0] + "')")
            data = line.split(':', 1)[1][:8].rstrip('\r\n')

            try:
                if is_hex(data):
                    DATA[region] = data
                else:
                    raise ValueError("Reading region " + str(region) + ", string '" + data + "' is not hexadecimal.")
            except ValueError as exception:
                sys.exit('Invalid OTP Dump (' + str(exception) + ')')
        except IndexError:
            sys.exit('Invalid OTP Dump')
        except TypoError:
            sys.exit("Invalid OTP Dump. Please run 'vcgencmd otp_dump' to create file.")
    if not DATA:
        sys.exit("Invalid OTP Dump (empty file). Please run 'vcgencmd otp_dump' to create file.")

# only doing prints and just-in-time parsing if running as main script (as opposed to being imported as a library)

if __name__ == "__main__":
    read_otp_file()
    process_bootmode()
    process_serial()
    process_revision()

    print('               Control Register :', get('control', 'hex'), get('control', 'binary'))
    print('JTAG_DEBUG_KEY_PARITY_START_BIT :', pretty_string(control('bits_24-31')))
    print(' VPU_CACHE_KEY_PARITY_START_BIT :', pretty_string(control('bits_16-23')))
    print('               JTAG_DISABLE_BIT :', control('bit_15'))
    print('     JTAG_DISABLE_REDUNDANT_BIT :', control('bit_14'))
    print('          MACROVISION_START_BIT :', control('bit_13'))
    print('MACROVISION_REDUNDANT_START_BIT :', control('bit_11'))
    print('    DECRYPTION_ENABLE_FOR_DEBUG :', control('bit_9'))
    print('                ARM_DISABLE_BIT :', control('bit_7'))
    print('      ARM_DISABLE_REDUNDANT_BIT :', control('bit_6'))
    print('                       Bootmode :', get('bootmode', 'hex'), get('bootmode', 'binary'))
    print('                Bootmode - Copy :', get('bootmode_copy', 'hex'), get('bootmode_copy', 'binary'))
    print('          OSC Frequency 19.2MHz :', bootmode('bit_1'))
    print('            SDIO Pullup Enabled :', bootmode('bit_3'))
    print('               Bootmode (Bit 4) :', bootmode('bit_4'))
    print('               Bootmode (Bit 5) :', bootmode('bit_5'))
    print('               Bootmode (Bit 7) :', bootmode('bit_7'))
    print('                  GPIO Bootmode :', bootmode('bit_19'))
    print('             GPIO Bootmode Bank :', bootmode('bit_20'))
    print('                SD Boot Enabled :', bootmode('bit_21'))
    print('                      Boot Bank :', bootmode('bit_22'))
    print('         Bootmode (eMMC Enable) :', bootmode('bit_25'), '(This is not confirmed but is set on the CM3)')
    print('        USB Device Boot Enabled :', bootmode('bit_28'))
    print('          USB Host Boot Enabled :', bootmode('bit_29'))
    print('    Boot Signing Parity (15-0)  :', pretty_string(boot_signing_parity('bits_0-15')))
    print('    Boot Signing Parity (31-16) :', pretty_string(boot_signing_parity('bits_16-31')))
    print('                  Serial Number :', get('serial_number', 'hex'))
    print('          Inverse Serial Number :', get('serial_number_inverted', 'hex'))
    print('                Revision Number :', get('revision_number', 'hex'))
    print('              New Revision Flag :', revision('new_flag'))
    print('                            RAM :', MEMORY_SIZES_AS_STRING[BOARD['memory']], "MB")
    print('                   Manufacturer :', MANUFACTURERS_AS_STRING[BOARD['manufacturer']])
    print('                            CPU :', PROCESSORS_AS_STRING[BOARD['processor']])
    print('                     Board Type :', 'Raspberry Pi Model ' + BOARD_TYPES_AS_STRING.get(BOARD['type'], "{} (unknown)".format(bin(int(BOARD["type"], 2))) ) )
    print('                 Board Revision :', BOARD_REVISIONS_AS_STRING[BOARD['revision']])
    print('                   Batch Number :', get('batch_number', 'hex'))
    print('        Overvolt Protection Bit :', overclock('overvolt_protection'))
    print('            Customer Region One :', get('customer_one', 'hex'))
    print('            Customer Region Two :', get('customer_two', 'hex'))
    print('          Customer Region Three :', get('customer_three', 'hex'))
    print('           Customer Region Four :', get('customer_four', 'hex'))
    print('           Customer Region Five :', get('customer_five', 'hex'))
    print('            Customer Region Six :', get('customer_six', 'hex'))
    print('          Customer Region Seven :', get('customer_seven', 'hex'))
    print('          Customer Region Eight :', get('customer_eight', 'hex'))
    print('              MPEG2 License Key :', get('codec_key_one', 'hex'))
    print('               VC-1 License Key :', get('codec_key_two', 'hex'))
    print('                    MAC Address :', format_mac())
    print('                  Advanced Boot :', get('advanced_boot', 'hex'), get('advanced_boot', 'binary'))
    print('             ETH_CLK Output Pin :', pretty_string(advanced_boot('bits_0-6'), False))
    print('         ETH_CLK Output Enabled :', advanced_boot('bit_7'))
    print('             LAN_RUN Output Pin :', pretty_string(advanced_boot('bits_8-14'), False))
    print('         LAN_RUN Output Enabled :', advanced_boot('bit_15'))
    print('                USB Hub Timeout :', process_hub_timeout(advanced_boot('bit_24')))
    print('              ETH_CLK Frequency :', process_eth_clk_frequency(advanced_boot('bit_25')))
