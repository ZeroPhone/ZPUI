menu_name = "Pomodoro"

from time import sleep
from datetime import datetime
from threading import Lock

from zpui_lib.ui import Menu, MenuExitException, Refresher
from zpui_lib.helpers import setup_logger, read_or_create_config, local_path_gen, save_config_gen, BackgroundRunner, BooleanEvent, is_emulator, get_platform
from zpui_lib.libs.hw import beepy as beepy_lib

local_path = local_path_gen(__name__)
logger = setup_logger(__name__, "info")

state_file = "state.yaml"
save_state = save_config_gen(local_path(state_file))

state_default = """state: 'off'
start: ''
work_duration: 25
break_duration: 5
"""

# possible states:
# work, break, off, waiting_for_break, waiting_for_work

state_to_colors = {
  "work": "sea",
  "waiting_for_break":"yellow",
  "break":"purple",
  "waiting_for_work":"emerald",
  "off":"off"
}

state = read_or_create_config(local_path(state_file), state_default, menu_name+" app")

br = None
is_running = BooleanEvent()
save_state_lock = Lock()

# set led_num to -1 in state config file to disable LED output
has_led = None
led_num = 0

time_format = "%d-%m-%y %H:%M:%S.%f"

def save_state_locked():
    with save_state_lock:
        save_state(state)

def get_start_time():
    ts = state["start"]
    time = datetime.strptime(ts, time_format) if ts else datetime.now()
    return time

def minutes_since():
    time = get_start_time()
    now = datetime.now()
    result = ((now-time).total_seconds())//60
    return int(result)

def save_time():
    state["start"] = datetime.now().strftime(time_format)
    save_state_locked()

def watcher():
    # thread that watches and checks time since last set. bery simple.
    while is_running:
        if get_state() == "work":
            if minutes_since() >= state["work_duration"]:
                set_state("waiting_for_break")
        elif get_state() == "waiting_for_work":
            timeout_minutes = (state["break_duration"]+state["work_duration"])*2
            if minutes_since() >= timeout_minutes: # app abandoned?
                set_state("off")
        elif get_state() == "break":
            if minutes_since() >= state["break_duration"]:
                set_state("waiting_for_work")
        elif get_state() == "waiting_for_break":
            timeout_minutes = (state["break_duration"]+state["work_duration"])*2
            if minutes_since() >= timeout_minutes:
                set_state("off")
        # might've been turned off if timeouted, let's stop it right after turnoff
        if get_state() == "off":
            is_running.clear()
            return
        sleep(10)

def set_led(state):
    if (has_led and led_num >= 0) or is_emulator():
        if state in state_to_colors:
            color = state_to_colors[state]
        else:
            logger.error(f"Color for state {state} not found!")
            color = "red"
        if color in beepy_lib.colors:
            color_rgb = beepy_lib.colors[color]
        else:
            logger.error(f"Color {state} not found in beepy lib!")
            color_rgb = (10, 0, 0)
        if not is_emulator():
            beepy_lib.led_write(*color_rgb, led_num)
        else:
            logger.debug(f"Would display color {color} ({color_rgb})")

def status_refresher_data():
    data = []
    data.append(f"State: {get_state().replace('_', ' ')}".center(o.cols))
    if get_state().endswith("work") or get_state().endswith("break"):
        minutes = state["work_duration"] if get_state().endswith("work") else state["break_duration"]
        data.append(f"Minutes: {minutes_since()}/{minutes}".center(o.cols))
    else:
        data.append("")
    data.append("UP: work/break;".center(o.cols))
    data.append("RIGHT: on/off;".center(o.cols))
    #data.append("ENTER: menu;")
    return data

def get_state():
    return state["state"]

def check_log_state(initial=False):
    if get_state() == "off":
        is_running.clear()
    else:
        is_running.set()
        if not br.running:
            logger.debug(f"Starting runner!")
            br.run()
    if not initial:
        logger.info(f"New state: {get_state()} at {get_start_time()}")

def set_state(new_state):
    logger.debug(f"New state: {get_state()} at {get_start_time()}")
    state["state"] = new_state
    set_led(new_state)
    save_state_locked()

def toggle_on_off_ui():
    if get_state() == "off":
        set_state("work")
    elif get_state() in ["break", "work"]:
        set_state("off")
    else: # no change made right now
        return
    save_time()
    check_log_state()

def toggle_work_break_ui():
    if get_state() in ["off", "break", "waiting_for_break"]:
        set_state("work")
    elif get_state() in ["work", "waiting_for_work"]:
        set_state("break")
    else:
        return
    save_time()
    check_log_state()

"""
def start_monitoring_ui():
    pass

def start_break_ui():
    pass

def stop_monitoring_ui():
    pass

def ack_notification_ui():
    pass

def settings_ui():
    pass

def pomodoro_options_menu():
    menu_contents = [
      ["Acknowledge", ack_notification_ui],
      ["Start", start_monitoring_ui],
      ["Start break", start_break_ui],
      ["Stop", stop_monitoring_ui],
      ["Settings", settings_ui]
    ]
    Menu(menu_contents, i, o, "Pomodoro options menu").activate()
"""

def init_app(input, output):
    global i, o, br, has_led, led_num
    i = input; o = output
    br = BackgroundRunner(watcher)
    if beepy_lib.driver_loaded():
        platform = get_platform()
        beepy_lib.set_device_from_platform(platform)
        has_led = True
    if has_led:
        # right top LED if on snowdive, else just the usual LED
        led_num_default = 2 if "snowdive" in platform else 0
        led_num = state.get("led_num", led_num_default)
    check_log_state(initial=True)

def callback():
    # menu disabled, there's not much use in it for now until it acquires like, settings
    #keymap = {"KEY_ENTER":pomodoro_options_menu, "KEY_RIGHT":toggle_on_off_ui, "KEY_UP":toggle_work_break_ui}
    keymap = {"KEY_RIGHT":toggle_on_off_ui, "KEY_UP":toggle_work_break_ui}
    refresher = Refresher(status_refresher_data, i, o, 3, keymap, "Pomodoro monitor")
    refresher.activate()
