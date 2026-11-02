from zpui_lib.ui import MockOutput, Canvas ,Zone, ZoneSpacer as ZS, \
                 VerticalZoneSpacer as VZS, ZoneManager, crop, Checkbox
from zpui_lib.helpers import setup_logger, read_or_create_config, local_path_gen, save_config_gen, rpc_api as api

import json
from copy import copy
from datetime import datetime

logger = setup_logger(__name__, "info")

menu_name = "Notifications receiver [un-openable app]"

context = None
i = None; o = None

local_path = local_path_gen(__name__)

default_config = "history_file:history.log"
config = read_or_create_config(local_path("config.yaml"), default_config, menu_name+" app")
save_config = save_config_gen(local_path("config.yaml"))

notification_storage = None

def can_load():
    return True

def init_app(inp, outp):
    global i, o, notification_storage
    i = inp; o = outp
    notification_storage = []

def receive_notifs(data, parameters=0):
    logger.debug(f"Received notification {json.dumps(data)}, params {parameters}")
    process_notification(data)
    log_notification(data)
    statusbar_zone.request_refresh()
    return api.RETURN_NOTIFY_SUCCESS, ""

def process_notification(data):
    # only one version possible for now
    notification_storage.append(data)

# zeromenu entry

def draw_statusbar_notifications(zone, value, limit):
    # a function where most of the code is dedicated to an ability to "..." notification text if it is too long
    #print("NOTIF REDRAW", value, limit)
    font_size = int(zone.canvas.height // 2.5)
    font = zone.canvas.decypher_font_reference(("Mukta-SemiBold.ttf", font_size))
    zone.canvas.clear()
    text_width = lambda x: zone.canvas.draw.textbbox((0, 0), x, font=font)[2]
    ddd = "..."
    ddd_width = text_width(ddd)
    current_width = text_width(value)
    zone.canvas.clear() # canvas probably not modified by getbbox but i dont wanna debug the case that it does
    left_offset = 4
    if limit != None and (current_width+left_offset > limit):
        # binary search-ish for 3 iterations, quick and dirty enough
        new_text_len = len(value)//2 # start with half-text
        new_text_width = text_width(value[:new_text_len]+ddd)
        for i in range(5):
            portion = int(len(value)*(1/(2**(i+2))))
            new_text_width = text_width(value[:new_text_len]+ddd)
            if new_text_width+left_offset+ddd_width > limit:
                new_text_len -= portion
            else:
                new_text_len += portion
                new_text_width = text_width(value[:new_text_len]+ddd)
                if new_text_width+left_offset+ddd_width > limit: # +='ed too far
                    new_text_len -= portion # heck go back, we try again next time with smaller portion
        while new_text_width+left_offset+ddd_width > limit: # wow, still too long after three careful bisections
            new_text_len = int(0.9*new_text_len) # moving forward one 3/4th at a time
            new_text_width = text_width(value[:new_text_len]+ddd)
        new_text = value[:new_text_len]+ddd
        #print(new_text)
        zone.canvas.clear()
        zone.canvas.text(new_text, (zone.o_params["height"]-5, left_offset), font=font)
    else:
        zone.canvas.text(value, (zone.o_params["height"]-5, left_offset), font=font)
    return crop(zone.canvas.get_image(), min_height=zone.o_params["height"], align="vcenter")

"""
Planned implementation:
- logs replayed into storage
- ability to view history
For now:
- per-launch storage, no replay
"""

def get_last_notif():
    if notification_storage:
        last_data = notification_storage[-1]
        msg = last_data.get("msg", "Missing notification message!")
        if len(notification_storage)>1:
            msg = f"({len(notification_storage)}) {msg}"
        return msg
    # notification't
    return "No notifications yet"

statusbar_zone = Zone(get_last_notif, draw_statusbar_notifications, name="Notifications", caching=True, trimmable=True)

def log_notification(data):
    # TODO datetime
    with open(local_path("todo_logfile.log"), "a") as f:
        try:
            data_str = json.dumps(data)
        except:
            logger.exception(f"Failed to serialize {data}!")
        f.write(data_str+'\n')

def set_context(c):
    global context
    if can_load() == True:
        context = c
        context.set_provider("statusbar_notifications", statusbar_zone)
        context.set_provider("notifications_receiver", receive_notifs)
        context.set_provider("settings_notifications", settings_notifications)

def settings_notifications():
    pass

settings_notifications.name = "Notification settings"

"""
    cb_contents = []
    statusbar_prefix = "statusbar_"
    providers = context.get_providers_by_type(statusbar_prefix)
    logger.debug("Found status bar zone providers: {}".format(providers))
    for name, zone in providers.items():
        hr_name = name[len(statusbar_prefix):].replace("_", " ").capitalize()
        cb_contents.append([hr_name, name, name not in config["disabled_items"]])
    #cb_contents.append(["Notifications", "notifs", "notifs" not in config["disabled_items"]])
    cb = Checkbox(cb_contents, i, o, name="Statusbar app item toggles setting")
    result = cb.activate()
    if result:
        for name, state in result.items():
            if not state:
                if name not in  config["disabled_items"]:
                    config["disabled_items"].append(name)
            elif state and name in config["disabled_items"]: # enabled but included in disabled items, removing
                config["disabled_items"].remove(name)
        save_config(config)
"""
