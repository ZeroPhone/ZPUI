from zpui_lib.ui import MockOutput, Canvas ,Zone, ZoneSpacer as ZS, \
                 VerticalZoneSpacer as VZS, ZoneManager, crop
from zpui_lib.helpers import setup_logger

from copy import copy

logger = setup_logger(__name__, "debug")

menu_name = "Status bar [un-openable app]"

status_bar = None
context = None
i = None; o = None

zones = {}
markup = []

def can_load():
    return True

def set_context(c):
    global context
    if can_load() == True:
        context = c
        status_bar = StatusBar()
        context.set_provider("status_bar", status_bar)

def execute_after_contexts():
    global zones, markup
    statusbar_prefix = "statusbar_"
    providers = context.get_providers_by_type(statusbar_prefix)
    logger.debug("Found status bar zone providers: {}".format(providers))
    for name, zone in providers.items():
        zone_name = name[len(statusbar_prefix):] # prefix removal
        zones[name] = zone
    """
    zones = {provider_name:
        "hh_mm":Zone(get_hh_mm, draw_hh_mm, name="HH_MM"),
         "ss":Zone(get_ss, draw_ss, name="SS"),
         "gsm":Zone(get_gsm, draw_gsm, name="gsm"),
         "wifi":Zone(get_wifi, draw_wifi, name="wifi"),
         "usb":Zone(get_usb, draw_usb, name="usb"),
         "display":Zone(get_display, draw_display, name="display"),
         "battery":Zone(get_battery, draw_battery, name="battery"),
        }
    """
    # currently-dummy zone for status bar notifs
    # this will soon get moved into a "Notifications" service app
    def draw_notifs(zone, value):
        text_size = int(zone.canvas.height // 2.5)
        zone.canvas.text("Notifications will go here", (zone.o_params["height"]-5, 4), font=("Mukta-SemiBold.ttf", text_size))
        return crop(zone.canvas.get_image(), min_height=zone.o_params["height"], align="vcenter")
    zones["notifs"] = Zone(lambda: True, draw_notifs, name="Notifications", trimmable=True)
    added_providers = (name for name in zones if name!= "notifs")
    markup = [[ZS(5), "notifs", "...", *added_providers, ZS(5)]]

class StatusBar():
    zm = None
    def __init__(self):
        pass

    def notify_update(self, name=None):
        pass
        #print("Default call 2 ugh")

    def output_image(self, c, height):
        #if canvas != c:
        #    canvas = c # making sure the canvas is saved for on-demand updates
        if not self.zm: # first invocation?
            # creating a zone manager if not present
            self.o = MockOutput(height=height, width=c.width, o=o)
            local_markup = copy(markup)
            local_markup[0] += [height]
            #print("ololo", local_markup)
            self.zm = ZoneManager(None, self.o, local_markup, zones)
            self.zm.notify_update = self.notify_update
        self.zm.update()
        statusbar_image = self.zm.get_image()
        c.clear((0, 0, c.width, height), )
        c.paste(statusbar_image, (0, 0))
