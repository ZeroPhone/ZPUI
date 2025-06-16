from zpui_lib.ui import Canvas, Refresher, Menu, MockOutput

def show_pinouts(i, o):
    zp_pinout = zp_pinouts_page(o).get_image()
    ua_pinout = uap_pinouts_page(o).get_image()
    isp_pinout = isp_pinouts_page(o).get_image()
    pk2_pinout = pk2_pinouts_page(o).get_image()
    show_pinout = lambda x: Refresher(lambda: x, i, o, name="Pinout display refresher").activate()
    contents = [["ZeroPhone side header", lambda: show_pinout(zp_pinout)],
                ["USB ASP", lambda: show_pinout(ua_pinout)],
                ["AVR ISP", lambda: show_pinout(isp_pinout)],
                ["PICkit2", lambda: show_pinout(pk2_pinout)]]
    Menu(contents, i, o, name="Pinout gallery page").activate()

def zp_pinouts_page(o):
    zpp = [['vcc'], ['gnd'], ['mosi'], ['miso'], ['sck'], ['rst']]
    c = Canvas(o)
    headline = "ZeroPhone"
    ctb = c.get_centered_text_bounds(headline)
    c.text(headline, (ctb.left+10, 2))
    c.text("Gamma pinout", (ctb.left+10, 12))
    c.text("(side header)", (ctb.left+10, 22))
    c = draw_pinout(c, o, zpp, lo=5)
    return c

def isp_pinouts_page(o):
    isp = [['miso', 'vcc'], ['sck', 'mosi'], ['rst', 'gnd']]
    c = Canvas(o)
    headline = "ISP header pinout"
    ctb = c.get_centered_text_bounds(headline)
    c.text(headline, (ctb.left, 2))
    c = draw_pinout(c, o, isp, lo=2)
    c = draw_pinout(c, o, isp, lo=2, reversed=True)
    ctb = c.get_centered_text_bounds("cable")
    c.text("board", (ctb.left/2-5, "-15"))
    c.text("cable", (ctb.left/2+c.width/2-5, "-15"))
    return c

def uap_pinouts_page(o):
    uap = [['mosi', 'vcc'], ['nc', 'txd'], ['rst', 'rxd'], ['sck', 'nc'], ['miso', 'gnd']]
    c = Canvas(o)
    headline = "USBASP pinout"
    ctb = c.get_centered_text_bounds(headline)
    c.text(headline, (ctb.left, 0))
    c = draw_pinout(c, o, uap, lo=2, ph=8, tto=-1)
    c = draw_pinout(c, o, uap, lo=2, ph=8, tto=-1, reversed=True)
    ctb = c.get_centered_text_bounds("cable")
    c.text("board", (ctb.left/2-5, str(-o.char_height-2)))
    c.text("cable", (ctb.left/2+c.width/2-5, str(-o.char_height-2)))
    return c

def pk2_pinouts_page(o):
    pkp = [['rst'], ['vcc'], ['gnd'], ['miso'], ['sck'], ['mosi']]
    c = Canvas(o)
    headline = "PICkit2"
    ctb = c.get_centered_text_bounds(headline)
    c.text(headline, (ctb.left+10, 2))
    c.text("pinout", (ctb.left+10, 12))
    c = draw_pinout(c, o, pkp, lo=5)
    return c

    pk2 = [['mosi', 'vcc'], ['nc', 'txd'], ['rst', 'rxd'], ['sck', 'nc'], ['miso', 'gnd']]
    c = Canvas(o)
    headline = "PicKit2 pinout"
    ctb = c.get_centered_text_bounds(headline)
    c.text(headline, (ctb.left, 0))
    c = draw_pinout(c, o, uap, lo=2, ph=8, tto=-1)
    c = draw_pinout(c, o, uap, lo=2, ph=8, tto=-1, reversed=True)
    ctb = c.get_centered_text_bounds("cable")
    c.text("board", (ctb.left/2-5, str(-o.char_height-2)))
    c.text("cable", (ctb.left/2+c.width/2-5, str(-o.char_height-2)))
    return c

def draw_pinout(c, o, t, ph=10, pw=30, lo=3, to=None, tto=0, reversed=False):
    rows = len(t)
    cols = max([len(x) for x in t])
    if to is None: to = (o.height-ph*rows)/2
    if lo is None: lo = (o.width-pw*cols)/2
    lx = lo + pw
    if reversed:
        c.rectangle((str(-lo), to, str(-(lo+pw*cols)), to+ph*rows))
        c.rectangle((str(-lo-1), to, str(-lo+1), to+ph), fill=c.default_color)
        c.line((str(-lx), to, str(-lx), to+ph*rows))
        for x in range(rows-1):
            c.line((str(-lo), to+ph*x+ph, str(-(lo+pw*cols)), to+ph*x+ph))
        for x in range(rows):
            if len(t[x]) > 1:
                c.text(t[x][1], (str(-lo-pw*2+5), to+ph*x+tto))
            c.text(t[x][0], (str(-lo-pw+5), to+ph*x+tto))
    else:
        c.rectangle((lo, to, lo+pw*cols, to+ph*rows))
        c.rectangle((lo+1, to, lo-1, to+ph), fill=c.default_color)
        c.line((lx, to, lx, to+ph*rows))
        for x in range(rows-1):
            c.line((lo, to+ph*x+ph, lo+pw*cols, to+ph*x+ph))
        for x in range(rows):
            c.text(t[x][0], (lo+5, to+ph*x+tto))
            if len(t[x]) > 1:
                c.text(t[x][1], (lo+pw+5, to+ph*x+tto))
    return c

def make_image_from_status(o, status, success_message=None):
    c = Canvas(o)
    if status[0] == "Success":
        c.bitmap((44, 3), get_yes_icon(o=o), fill=c.default_color)
        if success_message:
            status.append(success_message)
    else:
        c.bitmap((44, 3), get_no_icon(o=o), fill=c.default_color)
    top_start = 45
    top_increment = 10
    for i, s in enumerate(status[1:]):
        ctb = c.get_centered_text_bounds(s)
        c.text(s, (ctb.left, top_start+top_increment*i))
    return c.get_image()

def get_no_icon(width=40, height=40, o=None):
    o = MockOutput(width, height, o=o)
    c = Canvas(o)
    cx, cy = c.get_center()
    c.circle((cx, cy, min(width/2, height/2)-1), fill=c.default_color)
    c.line((cx-10, cy-10, cx+10, cy+10), fill=c.background_color, width=5)
    c.line((cx+10, cy-10, cx-10, cy+10), fill=c.background_color, width=5)
    return c.get_image()

def get_yes_icon(width=40, height=40, o=None):
    o = MockOutput(width, height, o=o)
    c = Canvas(o)
    cx, cy = c.get_center()
    c.circle((cx, cy, min(width/2, height/2)-1), fill=c.default_color)
    c.line((cx-15, cy, cx, cy+15), fill=c.background_color, width=5)
    c.line((cx-1, cy+15, cx+10, cy-12), fill=c.background_color, width=4)
    return c.get_image()
