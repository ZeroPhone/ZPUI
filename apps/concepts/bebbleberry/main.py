# -*- coding: utf-8 -*-
import os
import sys
import yaml
from datetime import datetime

from zpui_lib.apps.zero_app import ZeroApp
from zpui_lib.helpers import setup_logger, local_path_gen
from zpui_lib.ui import Menu, Printer, Canvas

local_path = local_path_gen(__name__)
logger = setup_logger(__name__, "info")

from PIL import Image

from resources import ResourceManager

class BebbleBerryApp(ZeroApp):
    font_size = 12

    def init_app(self):
        """gets called when ZPUI is starting"""
        self.menu_name = "BebbleBerry Emulator"  # App name as seen in main menu while using the system
        self.main_menu_contents = []
        self.c = Canvas(self.o)
        self.res = ResourceManager(self.c)
        self.apps = get_installed_apps()
        if self.o.device_mode == "1":
            self.res.wifi = self.res.wifi.point(lambda x: 255 if x>64 else 0)
            self.res.bluetooth = self.res.bluetooth.point(lambda x: 255 if x>127 else 0)
            self.res.battery_level[3] = self.res.battery_level[3].point(lambda x: 255 if x>250 else 0)
            self.res.bell = self.res.bell.point(lambda x: 255 if x>127 else 0)

    def draw_noti_bar(self):
        #breakpoint()
        # draw notifications bar
        self.c.rectangle((0, 0, self.o.width, 30), outline="black", fill="black")
        # draw system icons
        """
        print(self.res.wifi.mode)
        def p(i):
            sys.stdout.write(str(i)+' '+str(j)+' ')
            return i, j
        #self.c.paste(self.res.wifi.point(lambda x: 255 if x>100 else 0), (230, 8))
        sys.stdout.flush()
        """
        self.c.paste(self.res.wifi, (275, 8))
        self.c.paste(self.res.bluetooth, (295, 8))
        self.c.paste(self.res.battery_level[3], (315, 8))

        # draw time
        self.c.text(datetime.now().strftime("%I:%M %p"), (335, 5), font=(self.res.MukataSemiBold, self.font_size))

        # draw number of notifications
        self.c.paste(self.res.bell, (8, 8))
        self.c.text(f"{str(len(self.res.noti_q.queue))} notifications", (25, 4), font=(self.res.MukataSemiBold, self.font_size))
        return False

    def draw_menu(self):
        self.c.rectangle((0, 30, self.c.width, self.c.height), fill="white")

        for i, app in enumerate(self.apps):
            ## TODO: Make all of this math for figure out the app x and y actually make sense. Also pagenate
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

            # set app block colors based on whether the app is selected
            bg_color = "black" if i == self.selected else "white"
            text_color = "white" if i == self.selected else "black"
            fg_color = text_color
            icon = app["inverse_icon"] if i == self.selected else app["icon"]
            if app["name"] == "Beeper":
                if i == self.selected:
                    if self.o.device_mode == "1":
                        icon = app["inverse_icon"].point(lambda x: 255 if x>64 else 0)
                    else:
                        icon = app["inverse_icon"]
                else:
                    if self.o.device_mode == "1":
                        icon = app["icon"].point(lambda x: 255 if x>200 else 0)
                    else:
                        icon = app["icon"]

            # draw border
            self.c.rectangle((app_x, app_y, app_x+100, app_y+100), fill="black", outline="black")

            # draw background
            self.c.rectangle((app_x + 5, app_y + 5, app_x + 95, app_y + 95), fill=bg_color, outline="black")
            # get text size so we can center text
            #text_size = measure_text_ex(res.MukataSemiBold, app.get("name"), self.font_size, 0).x
            font_size = int(self.font_size*1.25) if i == self.selected else self.font_size
            font = self.c.decypher_font_reference((self.res.MukataSemiBold, font_size))
            _, _, text_size, _ = self.c.draw.textbbox((0, 0), app.get("name"), font=font)

            # draw app name
            self.c.text(
                app.get("name"),
                (app_x + int((100 - text_size) // 2), app_y + 72),
                font=(self.res.MukataSemiBold, font_size), fill=text_color
            )

            # draw icon
            self.c.paste(icon, (app_x + 25, app_y + 15))

        self.c.display()
        return False

    def key_callback(self, key, *args, **kwargs):
        #print(key, args, kwargs)
        # handle input. kinda hacky. I think ~~I~~ WE can do better, comrade
        if key == "KEY_DOWN":
            if self.selected + 4 < len(self.apps):
                self.selected += 4
            else:
                self.selected = len(self.apps)-1
        if key == "KEY_UP":
            if self.selected - 4 >= 0:
                self.selected -= 4
            else:
                self.selected = 0
        if key == "KEY_RIGHT":
            if self.selected + 1 < len(self.apps):
                self.selected += 1
            else:
                self.selected = len(self.apps)-1
        if key == "KEY_LEFT":
            if self.selected - 1 >= 0:
                self.selected -= 1
            else:
                self.selected = 0
        self.draw_menu()

    def on_start(self):
        """gets called when application is activated in the main menu"""
        self.draw_noti_bar()
        self.selected = 0

        self.draw_menu()
        self.i.set_streaming(self.key_callback)
        self.i.remove_maskable_callback("KEY_LEFT")
        self.i.listen()
        while True:
            import time
            time.sleep(1)


def get_installed_apps():
    apps = []
    for app in [app for app in os.listdir(local_path("apps")) if os.path.isdir(local_path(f"apps/{app}"))]:
        with open(local_path(f"apps/{app}/manifest.yml"), "r") as stream:
            try:
                manifest = yaml.safe_load(stream)
            except yaml.YAMLError:
                print(f"{app} does not have a manifest!! Aborting load")
        icon = Image.open(local_path(f"apps/{app}/res/launcher-icon.png"))
        inverse_icon = Image.open(local_path(f"apps/{app}/res/launcher-icon-inverse.png"))
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

