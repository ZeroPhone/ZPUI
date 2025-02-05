import psutil
import os

emulator_flag_filename = "emulator"

def zpui_running_as_service():
    if psutil.Process(os.getpid()).ppid() == 1:
        return True;
    else:
        return False;

def is_emulator():
    return emulator_flag_filename in os.listdir(".")
