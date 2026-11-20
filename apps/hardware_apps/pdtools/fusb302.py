from time import sleep
try:
    import smbus
except ImportError:
    smbus = None

########################
#
# FUSB-specific code
#
########################

class FUSB302():
    #FUSB302_I2C_SLAVE_ADDR = 0x22
    REG_DEVICE_ID = 0x01
    REG_SWITCHES0 = 0x02
    REG_SWITCHES1 = 0x03
    REG_MEASURE = 0x04
    REG_CONTROL0 = 0x06
    REG_CONTROL1 = 0x07
    REG_CONTROL2 = 0x08
    REG_CONTROL3 = 0x09
    REG_MASK = 0x0A
    REG_POWER = 0x0B
    REG_RESET = 0x0C
    REG_MASKA = 0x0E
    REG_MASKB = 0x0F
    REG_STATUS0A = 0x3C
    REG_STATUS1A = 0x3D
    REG_INTERRUPTA = 0x3E
    REG_INTERRUPTB = 0x3F
    REG_STATUS0 = 0x40
    REG_STATUS1 = 0x41
    REG_INTERRUPT = 0x42
    REG_FIFOS = 0x43

    def __init__(self, bus, addr=0x22, int_p=None):
        self.is_linux_smbus = smbus != None
        self.bus = bus
        self.addr = addr
        self.int_p = int_p

    def i2c_read(self, reg, amount=1):
        if self.is_linux_smbus:
            return self.bus.read_i2c_block_data(self.addr, reg, amount)
        else:
            return self.bus.readfrom_mem(self.addr, reg, amount)

    def i2c_write(self, reg, data):
        if self.is_linux_smbus:
            return self.bus.write_i2c_block_data(self.addr, reg, list(data))
        else:
            return self.bus.writeto_mem(self.addr, reg, data)

    def reset(self):
        # reset the entire FUSB
        self.i2c_write(self.REG_RESET, bytes([0b1]))

    def reset_pd(self):
        # resets the FUSB PD logic
        self.i2c_write(self.REG_RESET, bytes([0b10]))

    def unmask_all(self):
        # unmasks all interrupts
        self.i2c_write(self.REG_MASK, bytes([0b0]))
        self.i2c_write(self.REG_MASKA, bytes([0b0]))
        self.i2c_write(self.REG_MASKB, bytes([0b0]))

    def cc_current(self):
        # show measured CC level interpreted as USB-C current levels
        return self.i2c_read(self.REG_STATUS0, 1)[0] & 0b11

    def read_cc(self, cc):
        # enable a CC pin for reading
        assert(cc in [0, 1, 2])
        x = self.i2c_read(self.REG_SWITCHES0, 1)[0]
        x1 = x
        clear_mask = ~0b1100 & 0xFF
        x &= clear_mask
        mask = [0b0, 0b100, 0b1000][cc]
        x |= mask
        #print('self.REG_SWITCHES0: ', bin(x1), bin(x), cc)
        self.i2c_write(self.REG_SWITCHES0, bytes((x,)) )

    def enable_pullups(self):
        # enable host pullups on CC pins, disable pulldowns
        x = self.i2c_read(self.REG_SWITCHES0, 1)[0]
        x |= 0b11000000
        self.i2c_write(self.REG_SWITCHES0, bytes((x,)) )

    def set_mdac(self, value):
        x = self.i2c_read(self.REG_MEASURE, 1)[0]
        x &= 0b11000000
        x |= value
        self.i2c_write(self.REG_MEASURE, bytes((x,)) )

    def enable_sop(self):
        # enable reception of SOP'/SOP" messages
        x = self.i2c_read(self.REG_CONTROL1, 1)[0]
        mask = 0b1100011
        x |= mask
        self.i2c_write(self.REG_CONTROL1, bytes((x,)) )

    def disable_pulldowns(self):
        x = self.i2c_read(self.REG_SWITCHES0, 1)[0]
        clear_mask = ~0b11 & 0xFF
        x &= clear_mask
        self.i2c_write(self.REG_SWITCHES0, bytes((x,)) )

    def enable_pulldowns(self):
        x = self.i2c_read(self.REG_SWITCHES0, 1)[0]
        x |= 0b11
        self.i2c_write(self.REG_SWITCHES0, bytes((x,)) )

    def measure_sink(self, debug=False):
        # read CC pins and see which one senses the pullup
        self.read_cc(1)
        sleep(0.001)
        cc1_c = self.cc_current()
        self.read_cc(2)
        sleep(0.001)
        cc2_c = self.cc_current()
        # picking the CC pin depending on which pin can detect a pullup
        cc = [1, 2][cc1_c < cc2_c]
        if debug: print('m', bin(cc1_c), bin(cc2_c), cc)
        if cc1_c == cc2_c:
            return 0
        return cc

    def measure_source(self, debug=False):
        # read CC pins and see which one senses the correct host current
        self.read_cc(1)
        sleep(0.001)
        cc1_c = self.cc_current()
        self.read_cc(2)
        sleep(0.001)
        cc2_c = self.cc_current()
        if cc1_c == self.host_current:
            cc = 1
        elif cc2_c == self.host_current:
            cc = 2
        else:
            cc = 0
        if debug: print('m', bin(cc1_c), bin(cc2_c), cc)
        return cc

    def set_controls_sink(self):
        # boot: 0b00100100
        ctrl0 = 0b00000000 # unmask all interrupts; don't autostart TX.. disable pullup current
        ctrl0 |= self.host_current << 2 # enable only the pullup current bits that fusb is configured for
        self.i2c_write(self.REG_CONTROL0, bytes((ctrl0,)) )
        # boot: 0b00000110
        ctrl3 = 0b00000111 # enable automatic packet retries
        self.i2c_write(self.REG_CONTROL3, bytes((ctrl3,)) )

    host_current=0b10

    def set_controls_source(self):
        # boot: 0b00100100
        ctrl0 = 0b00000000 # unmask all interrupts; don't autostart TX
        ctrl0 |= self.host_current << 2 # set host current advertisement pullups
        self.i2c_write(self.REG_CONTROL0, bytes((ctrl0,)) )
        # boot: 0b00000110
        ctrl3 = 0b00000110 # no automatic packet retries
        self.i2c_write(self.REG_CONTROL3, bytes((ctrl3,)) )
        # boot: 0b00000010
        #ctrl2 = 0b00000000 # disable DRP toggle. setting it to Do Not Use o_o ???
        #self.i2c_write(self.REG_CONTROL2, bytes((ctrl2,)) )

    def set_wake(self, state):
        # boot: 0b00000010
        ctrl2 = self.i2c_read(self.REG_CONTROL2, 1)[0]
        clear_mask = ~(1 << 3) & 0xFF
        ctrl2 &= clear_mask
        if state:
            ctrl2 | (1 << 3)
        self.i2c_write(self.REG_CONTROL2, bytes((ctrl2,)) )

    def flush_receive(self):
        x = self.i2c_read(self.REG_CONTROL1, 1)[0]
        mask = 0b100 # flush receive
        x |= mask
        self.i2c_write(self.REG_CONTROL1, bytes((x,)) )

    def flush_transmit(self):
        x = self.i2c_read(self.REG_CONTROL0, 1)[0]
        mask = 0b01000000 # flush transmit
        x |= mask
        self.i2c_write(self.REG_CONTROL0, bytes((x,)) )

    def enable_tx(self, cc):
        # enables switch on either CC1 or CC2
        x = self.i2c_read(self.REG_SWITCHES1, 1)[0]
        x1 = x
        mask = 0b10 if cc == 2 else 0b1
        x &= 0b10011100 # clearing both TX bits and revision bits
        x |= mask
        x |= 0b100
        x |= 0b10 << 5 # revision 3.0
        #print('et', bin(x1), bin(x), cc)
        self.i2c_write(self.REG_SWITCHES1, bytes((x,)) )

    def set_roles(self, power_role = 0, data_role = 0):
        x = self.i2c_read(self.REG_SWITCHES1, 1)[0]
        x &= 0b01101111 # clearing both role bits
        x |= power_role << 7
        x |= data_role << 7
        self.i2c_write(self.REG_SWITCHES1, bytes((x,)) )

    def power(self):
        # enables all power circuits
        x = self.i2c_read(self.REG_POWER, 1)[0]
        mask = 0b1111
        x |= mask
        self.i2c_write(self.REG_POWER, bytes((x,)) )

    def polarity(self):
        # reads polarity and role bits from STATUS1A
        return (self.i2c_read(self.REG_STATUS1A, 1)[0] >> 3) & 0b111
        #'0b110001'

    def interrupts(self):
        # return all interrupt registers
        return self.i2c_read(self.REG_INTERRUPTA, 2)+self.i2c_read(self.REG_INTERRUPT, 1)

    def interrupt_a(self):
        # return all interrupt registers
        return self.i2c_read(self.REG_INTERRUPTA, 1)[0]

    def interrupt_b(self):
        # return all interrupt registers
        return self.i2c_read(self.REG_INTERRUPTB, 1)[0]

    def interrupt(self):
        # return all interrupt registers
        return self.i2c_read(self.REG_INTERRUPT, 1)[0]

    # interrupts are cleared just by reading them, it seems
    #def clear_interrupts(self):
    #    # clear interrupt
    #    self.i2c_write(self.REG_INTERRUPTA, bytes([0]))
    #    self.i2c_write(self.REG_INTERRUPT, bytes([0]))

    # this is a way better way to do things than the following function -
    # the read loop should be ported to this function, and the next ome deleted
    def rxb_state(self):
        # get read buffer interrupt states - (rx buffer empty, rx buffer full)
        st = self.i2c_read(self.REG_STATUS1, 1)[0]
        return ((st & 0b100000) >> 5, (st & 0b10000) >> 4)

    # TODO: yeet
    def rxb_state(self):
        st = self.i2c_read(self.REG_STATUS1, 1)[0]
        return ((st & 0b110000) >> 4, (st & 0b11000000) >> 6)

    def get_rxb(self, l=80):
        # read from FIFO
        return self.i2c_read(self.REG_FIFOS, l)

    def hard_reset(self):
        self.i2c_write(self.REG_CONTROL3, bytes([0b1000000]))
        return self.i2c_read(self.REG_CONTROL3, 1)

    def set_to_cc(self, cc):
        self.flush_receive()
        self.enable_tx(cc)
        self.read_cc(cc)
        self.flush_transmit()
        self.flush_receive()
        self.reset_pd()

    def find_cc(self, fn="measure_sink", debug=False):
        if isinstance(fn, str):
            fn = getattr(self, fn)
        cc = fn(debug=debug)
        if cc != 0:
            self.set_to_cc(cc)
        #import gc; gc.collect()
        return cc

    # FUSB toggle logic shorthands

    polarity_values = (
      (0, 0),   # 000: logic still running
      (1, 1),   # 001: cc1, src
      (2, 1),   # 010: cc2, src
      (-1, -1), # 011: unknown
      (-1, -1), # 100: unknown
      (1, 2),   # 101: cc1, snk
      (2, 2),   # 110: cc2, snk
      (0, 3),   # 111: audio accessory
    )

    polarity_names = {
      -1: "unknown",
       0:  "none",
       1:  "source",
       2:  "sink",
       3:  "audio",
    }

    current_values = (
        "Ra/low",
        "Rd-Default",
        "Rd-1.5",
        "Rd-3.0"
    )

    def set_toggle(self, state, mode=0b01, wake_en=0b1, rd_only=0b0, tg_pwrsave=0b00):
        #ctrl2 = self.i2c_read(self.REG_CONTROL2)[0]
        #ctrl2 &= (~0b11101111)&0xff # clear all except reserved
        ctrl2 = 0 # actually, just clear all to start with
        ctrl2 |= int(state) # TOGGLE bit
        ctrl2 |= mode << 1 # MODE bits (default DRP mode)
        ctrl2 |= wake_en << 3 # WAKE_EN bit, default on (enable Wake Detection functionality)
        ctrl2 |= rd_only << 5 # TOG_RD_ONLY bit, default both Rd and Ra
        ctrl2 |= tg_pwrsave << 6 # TOG_SAVE_PWR1/2 bits, default "don't go into DISABLE state" (no powersaving at all lol)
        self.i2c_write(self.REG_CONTROL2, bytes((ctrl2,)) )

    def str_pol(self):
        pol = self.polarity()
        val = self.polarity_values[pol]
        return val

    def str_int(self, a=None):
        if a is None:
            a = self.interrupts()
        return [bin(x) for x in a]

    def str_cur(self):
        return current_values[self.cc_current()]

    def send(self, message):
        sop_seq = [0x12, 0x12, 0x12, 0x13, 0x80]
        eop_seq = [0xff, 0x14, 0xfe, 0xa1]

        sop_seq[4] |= len(message)

        self.i2c_write(self.REG_FIFOS, bytes(sop_seq) )
        self.i2c_write(self.REG_FIFOS, bytes(message) )
        self.i2c_write(self.REG_FIFOS, bytes(eop_seq) )
