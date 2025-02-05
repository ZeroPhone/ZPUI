import os
from datetime import datetime
from subprocess import check_output, CalledProcessError, STDOUT

from helpers import read_or_create_config, local_path_gen, save_config_gen
from ui import Menu, Printer, PrettyPrinter, DialogBox, PathPicker, UniversalInput, TextReader

menu_name = "Scripts"  # App name as seen in main menu while using the system

scripts_dir = "s/"
config_filename = "config.json"
default_config = """{
"output_dir":"/home/pi",
"scripts":[
 {"path":"./s/login.sh",
  "name":"Hotspot login"},
 {"path":"./s/dmesg.sh",
  "name":"Last 100 dmesg lines"},
 {"path":"/root/backup.sh",
  "name":"Backup things",
  "args":["--everything", "--now"]},
 {"path":"mount",
  "name":"'mount' with -a",
  "args":["-a"]},
 {"path":"wget",
  "name":"wget google main page",
  "args":["http://www.google.com"]}
],
"history":[]
}"""

local_path = local_path_gen(__name__)
config_path = local_path(config_filename)
config = read_or_create_config(config_path, default_config, menu_name + " app")
save_config = save_config_gen(config_path)


def call_external(script_list, shell=False):
    if shell:
        script_path = script_list.split(' ')[0]
    else:
        script_path = os.path.split(script_list[0])[1]
    Printer("Calling {}".format(script_path), i, o, 1)

    output = None
    try:
        output = check_output(script_list, stderr=STDOUT, shell=shell)
    except OSError as e:
        if e.errno == 2:
            Printer("File not found!", i, o, 1)
        elif e.errno == 13:
            Printer(["Permission", "denied!"], i, o, 1)
        elif e.errno == 8:
            Printer(["Unknown format,", "forgot header?"], i, o, 1)
        else:
            error_message = "Unknown error! \n \n {}".format(e)
            PrettyPrinter(error_message, i, o, 3)
        output = ""
    except CalledProcessError as e:
        Printer(["Failed with", "code {}".format(e.returncode)], i, o, 1)
        output = e.output
    else:
        Printer("Success!", i, o, 1)
    finally:
        if not output:
            return
        answer = DialogBox("yn", i, o, message="Show output?").activate()
        if answer:
            TextReader(output, i, o, autohide_scrollbars=True, h_scroll=True).activate()
            answer = DialogBox("yn", i, o, message="Save output?").activate()
            if answer:
                save_output(script_list, output)


def save_output(command, output):
    if not isinstance(command, basestring):
        command = " ".join(command)
    command = command.lstrip("/").replace("/", "_")
    now = datetime.now()
    filename = "log-{}-{}".format(command, now.strftime("%y%m%d-%H%M%S"))
    print(filename)
    old_dir = config["output_dir"]
    dir = PathPicker(old_dir, i, o, dirs_only=True).activate()
    if not dir:
        return
    # Saving the path into the config
    config["output_dir"] = dir
    save_config(config)
    path = os.path.join(dir, filename)
    print(path)
    with open(path, "w") as f:
        f.write(output)

def call_by_path():
    path = PathPicker("/", i, o).activate()
    if path is None:
        return
    args = UniversalInput(i, o, message="Arguments:", name="Script argument input").activate()
    if args is not None:
        path = path + " " + args
    call_external(path, shell=True)
    if path not in config["history"]:
        config["history"] = [path] + config["history"]
        save_config(config)

def call_command(command=None):
    if not command:
        command = UniversalInput(i, o, message="Command:", name="Script command input").activate()
        if not command:
            return
    call_external(command, shell=True)
    if command not in config["history"]:
        config["history"] = [command] + config["history"]
        save_config(config)

def exec_history_entry(num):
    call_command(config["history"][num])

def del_history_entry(num):
    answer = DialogBox("yn", i, o, message="Delete entry?").activate()
    if answer:
        config["history"].pop(num)
        save_config(config)

def history_menu():
    def get_mc():
        c = []
        for i, entry in enumerate(config["history"]):
            exec_e = lambda x=i: exec_history_entry(x)
            del_e = lambda x=i: del_history_entry(x)
            c.append([entry, exec_e, del_e])
        return c
    Menu([], i, o, contents_hook=get_mc, name="Scripts app history menu").activate()


def callback():
    script_menu_contents = [["Script by path", call_by_path],
                            ["Custom command", call_command],
                            ["History", history_menu],
                           ]
    scripts_in_config = []
    for script_def in config["scripts"]:
        script_path = script_def["path"]
        if script_path.startswith('./'):
            script_path = script_path.lstrip('.').lstrip('/')
            script_path = local_path(script_path)
            scripts_in_config.append(script_path)
        args = script_def["args"] if "args" in script_def else []
        script_name = script_def["name"] if "name" in script_def else os.path.split(script_path)[1]
        script_list = [script_path] + args
        script_menu_contents.append([script_name, lambda x=script_list: call_external(x)])
    other_scripts = os.listdir(local_path(scripts_dir))
    for script in other_scripts:
        relpath = local_path(scripts_dir, script)
        if relpath not in scripts_in_config:
            script_menu_contents.append([os.path.join(scripts_dir, script), lambda x=relpath: call_external([x])])
    Menu(script_menu_contents, i, o, "Script menu").activate()


i = None
o = None


def init_app(input_obj, output_obj):
    global i, o
    i = input_obj
    o = output_obj
