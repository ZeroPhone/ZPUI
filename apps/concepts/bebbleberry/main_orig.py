import os
import sys
sys.exit(0)
from datetime import datetime

import yaml
#from pyray import *

from resources import ResourceManager


def get_installed_apps():
    apps = []
    for app in [app for app in os.listdir("apps") if os.path.isdir(f"apps/{app}")]:
        with open(f"apps/{app}/manifest.yml", "r") as stream:
            try:
                manifest = yaml.safe_load(stream)
            except yaml.YAMLError:
                print(f"{app} does not have a manifest!! Aborting load")
        icon = load_texture(f"apps/{app}/res/launcher-icon.png")
        inverse_icon = load_texture(f"apps/{app}/res/launcher-icon-inverse.png")
        app = {
            "name": manifest["name"],
            "developer": manifest["developer"],
            "version": manifest["version"],
            "launch_file": manifest["launch_file"],
            "icon": icon,
            "inverse_icon": inverse_icon
        }
        apps.append(app)

    return apps


def draw_noti_bar(res):
    # draw notifications bar
    draw_rectangle(0, 0, res.s_width, 30, BLACK)

    # draw system icons
    draw_texture(res.wifi, 275, 8, WHITE)
    draw_texture(res.bluetooth, 295, 8, WHITE)
    draw_texture(res.battery_level[3], 315, 8, WHITE)

    # draw time
    draw_text_ex(res.MukataSemiBold, datetime.now().strftime("%I:%M %p"), Vector2(335, 5), 24, 0,
                 WHITE)

    # draw number of notifications
    draw_texture(res.bell, 8, 8, WHITE)
    draw_text_ex(res.MukataSemiBold, f"{str(len(res.noti_q.queue))} notifications", Vector2(25, 4), 24, 0, WHITE)
    return False


def draw_menu(res, apps, selected):
    for app in apps:
        ## TODO: Make all of this math for figure out the app x and y actually make sense. Also pagenate
        i = apps.index(app)
        a = 0
        if i > 0:
            a = 5
        app_x = 8 + (i * 100) - a * i
        app_y = 37

        # super hacky way to add a second row. cannot math to figure this one out right now
        if i > 3:
            app_y += 95
            x = i - 4
            app_x = 8 + (x * 100) - a * x

        # set colors based on if selected
        bg_color = BLACK if i == selected else WHITE
        text_color = WHITE if i == selected else BLACK
        icon = app["inverse_icon"] if i == selected else app["icon"]

        # draw border
        draw_rectangle(app_x, app_y, 100, 100, BLACK)

        # draw background
        draw_rectangle(app_x + 5, app_y + 5, 90, 90, bg_color)

        # get text size so we can center text
        text_size = measure_text_ex(res.MukataSemiBold, app.get("name"), 24, 0).x

        # draw app name
        draw_text_ex(res.MukataSemiBold, app.get("name"), Vector2(app_x + int((100 - text_size) / 2), app_y + 72), 24,
                     0, text_color)

        # draw icon
        draw_texture(icon, app_x + 25, app_y + 15, text_color)

    return False


def main():
    s_width = 400
    s_height = 240

    ## create emulation window
    init_window(s_width, s_height, "BebbleBerry Emulator")
    res = ResourceManager()

    ## loads apps from disk
    apps = get_installed_apps()

    selected = 0
    app_launched = False

    # draw blank screen

    while not window_should_close():
        if not app_launched:
            # handle input. kinda hacky. I think I can do better
            if is_key_pressed(264) and selected + 4 < len(apps):
                selected += 4
            if is_key_pressed(265) and selected - 4 >= 0:
                selected -= 4
            if is_key_pressed(262) and selected + 1 < len(apps):
                selected += 1
            if is_key_pressed(263) and selected - 1 >= 0:
                selected -= 1

            begin_drawing()

            clear_background(WHITE)
            draw_menu(res, apps, selected)
            draw_noti_bar(res)
            end_drawing()

    close_window()


if __name__ == "__main__":
    main()
