from __future__ import division

import math
import os
import time
from datetime import datetime, timedelta
from dateutil.zoneinfo import getzoneinfofile_stream, ZoneInfoFile

from subprocess import check_output, CalledProcessError

from apps import ZeroApp
from actions import FirstBootAction
from ui import Menu, Refresher, Canvas, IntegerAdjustInput, Listbox, LoadingBar, PrettyPrinter as Printer, PurposeOverlay

from helpers import read_or_create_config, local_path_gen, setup_logger

logger = setup_logger(__name__, "warning")
local_path = local_path_gen(__name__)

class ClockApp(ZeroApp, Refresher):

    def __init__(self, i, o, *args, **kwargs):
        super(ClockApp, self).__init__(i, o)
        self.menu_name = "Clock"
        self.countdown = None
        self.refresher = Refresher(self.on_refresh, i, o, keymap={"KEY_RIGHT":self.countdown_settings, "KEY_DOWN":self.force_sync_time})
        default_config = '{}'
        config_filename = "config.json"
        self.config = read_or_create_config(local_path(config_filename), default_config, self.menu_name+" app")

    def set_context(self, c):
        self.context = c
        c.register_firstboot_action(FirstBootAction("set_timezone", self.set_timezone, depends=None, not_on_emulator=True))
        c.register_firstboot_action(FirstBootAction("force_sync_time", self.force_sync_time, depends=["set_timezone", "check_connectivity"], not_on_emulator=True))

    def force_sync_time(self):
        Printer("Syncing time", self.i, self.o, 0)
        try:
            output = check_output(["sntp", "-S", "pool.ntp.org"])
        except CalledProcessError:
            logger.exception("Failed to sync time!")
            Printer("Failed to sync time!", self.i, self.o, 1)
            return False
        except OSError:
            logger.exception("Failed to sync time - sntp not installed!")
            Printer("Failed to sync time (no sntp)!", self.i, self.o, 1)
            return False
        else:
            Printer("Synced time successfully!", self.i, self.o, 1)
            return True

    def format_countdown(self):
        if not self.countdown: return None
        h, m, s, sign = self.get_countdown_time_left()
        if sign: return None
        return "{}m".format(h*60+m)

    def get_countdown_time_left(self):
        delta = self.countdown["time"]-datetime.now()
        print(delta)
        seconds = delta.seconds
        sign = None
        if delta.days < 0:
            seconds = -seconds
            sign = "+"
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if sign == "+":
            hours = hours+24
        return hours, minutes, seconds, sign

    def countdown_settings(self):
        # Setting an absolute countdown is not yet possible
        # because we don't yet have a TimePicker UI element
        def gmc(): #get menu contents
            countdown_label = self.format_countdown()
            contents = []
            if countdown_label: contents.append(["Countdown: {}".format(countdown_label)])
            #contents.append(["Set absolute", lambda: self.set_countdown(absolute=True)])
            contents.append(["Set relative", self.set_countdown])

            # Add an option for setting the timezone
            contents.append(["Set timezone", self.set_timezone])
            return contents
        Menu([], self.i, self.o, "Countdown settings menu", contents_hook=gmc).activate()

    def set_countdown(self, absolute=False):
        if absolute: raise NotImplementedError # Needs a TimePicker or something like that
        rel_start = 0
        message = "After (in minutes):"
        if self.countdown:
            # A countdown is already active
            # Using it as a starting point
            h, m, s, _ = self.get_countdown_time_left()
            rel_start = h*60+m
        offset = IntegerAdjustInput(rel_start, self.i, self.o, message=message).activate()
        if offset is not None:
            countdown = {"time": datetime.now()+timedelta(minutes=offset)}
            self.countdown = countdown

    # Shows a menu of available timezones, accept new TZ by pressing ENTER
    def set_timezone(self):

        try:
            with open('/etc/timezone', "r") as f:
                current_timezone = f.readline().strip()
        except:
            logger.exception("Can't get current timezone!")
            current_timezone = None
        else:
            logger.info("Current timezone: {}".format(repr(current_timezone)))

        lc = []
        with LoadingBar(self.i, self.o, message="Getting timezones"):
            for k in ZoneInfoFile(getzoneinfofile_stream()).zones.keys():
                lc.append([k])
        lc = sorted(lc)
        lb = Listbox(lc, self.i, self.o, "Timezone selection listbox", selected=current_timezone)
        lb.apply(PurposeOverlay(purpose="Select timezone"))
        choice = lb.activate()
        if choice:
            # Setting timezone using timedatectl
            try:
                check_output(["timedatectl", "set-timezone", choice])
            except CalledProcessError as e:
                logger.exception("Can't set timezone using timedatectl! Return code: {}, output: {}".format(e.returncode, repr(e.output)))
                return False
            else:
                logger.info("Set timezone successfully")
                return True
        else:
            return None

    def draw_analog_clock(self, c, time, radius="min(*c.size) / 3", clock_x = "center_x+32", clock_y = "center_y+5", h_len = "radius / 2", m_len = "radius - 5", s_len = "radius - 3", **kwargs):
        """Draws the analog clock, with parameters configurable through config.json."""
        center_x, center_y = c.get_center()
        clock_x = eval(clock_x)
        clock_y = eval(clock_y)
        radius = eval(radius)
        c.ellipse((clock_x - radius, clock_y - radius, clock_x + radius, clock_y + radius), fill=False, outline="white")
        self.draw_needle(c, 60 - time.second / 60, eval(s_len), clock_x, clock_y, 1)
        self.draw_needle(c, 60 - time.minute / 60, eval(m_len), clock_x, clock_y, 1)
        self.draw_needle(c, 24 - time.hour / 24, eval(h_len), clock_x, clock_y, 1)

    def draw_countdown(self, c, countdown_x="(center_x/2)-10", countdown_y="center_y/2*3", **kwargs):
        """Draws the digital clock, with parameters configurable through config.json."""
        h, m, s, sign = self.get_countdown_time_left()
        hz, mz, sz = map(lambda x:str(x).zfill(2), (h, m, s))
        string = "{}:{}".format(mz, sz)
        if h: string = hz+":"+string
        if sign: string = sign+string
        center_x, center_y = c.get_center()
        centered_coords = c.get_centered_text_bounds(string)
        x = eval(countdown_x)
        y = eval(countdown_y)
        c.text((x, y), string, fill="white")

    def draw_text(self, c, time, text_x="10", text_y="center_y-5", time_format = "%H:%M:%S", **kwargs):
        """Draws the digital clock, with parameters configurable through config.json."""
        time_str = time.strftime(time_format)
        center_x, center_y = c.get_center()
        centered_coords = c.get_centered_text_bounds(time_str)
        x = eval(text_x)
        y = eval(text_y)
        c.text(time_str, (x, y))

    def on_refresh(self):
        current_time = datetime.now()
        return self.render_clock(current_time, **self.config)

    def render_clock(self, time, **kwargs):
        c = Canvas(self.o)
        width, height = c.size
        self.draw_text(c, time, **kwargs)
        self.draw_analog_clock(c, time, **kwargs)
        if self.countdown:
            self.draw_countdown(c, **kwargs)
        return c.get_image()

    def draw_needle(self, c, progress, radius, x, y, width):
        # type: (Canvas, float, float, float, float, int) -> None
        hour_angle = math.pi * 2 * progress + math.pi
        c.line(
            (
                int(x),
                int(y),
                int(x + radius * math.sin(hour_angle)),
                int(y + radius * math.cos(hour_angle))
            ),
            width=width,
            fill=True
        )

    def on_start(self):
        self.refresher.activate()
