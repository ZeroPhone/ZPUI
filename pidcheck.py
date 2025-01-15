import os
import sys
import psutil
import subprocess
from select import select

from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "info")

def pid_problem_cli(cli_timeout=10):
    logger.info("Waiting for user input")
    print("\nWhat do you want to do?\n\n(C)ontinue and rewrite PID file\n(S)top/(Q)uit")
    has_char, _, _ = select([sys.stdin], [], [], cli_timeout)
    if has_char:
        if sys.stdin.read(1).lower() in "sq":
            sys.exit(1)
        else:
            print("Ok, moving on")

def process_exists_cli(pid, cli_timeout=10):
    logger.info("Waiting for user input")
    print("\nWhat do you want to do?\n\n(K)ill other process and continue booting\n(C)ontinue and rewrite PID file\n(S)top/(Q)uit\n(D)o nothing")
    has_char, _, _ = select([sys.stdin], [], [], cli_timeout)
    if has_char:
        char = sys.stdin.read(1).lower()
        if char in "sq":
            sys.exit(1)
        elif char == "k":
            return True
    else:
        print("No decision taken")

def create_pid(path):
    with open(path, 'w') as f:
        f.write(str(os.getpid()))

def kill_process(pid):
    try:
        os.kill(pid, 15)
    except OSError:
        logger.warning("Killing the previous process didn't work!")
    else:
        logger.info("Killed the previous process, continuing")

def zpui_process_still_running(pid):
    # A heuristic to recognize a ZPUI process semi-efficiently
    return psutil.pid_exists(pid) and "python" in psutil.Process(pid).name()

def check_and_create_pid(path, interactive=True, kill_not_stop=False):
    logger.info("Checking if another instance of ZPUI is running.")
    pid = None
    if os.path.isfile(path):
        try:
            pid = int(open(path, 'r').read().strip())
        except:
            logger.warning(path + " contents can't be read or parsed")
            if interactive:
                pid_problem_cli()
            else:
                pass
        if pid == os.getpid():
            logger.info("Current PID is already in the pidfile, all good")
            return
    if pid and zpui_process_still_running(pid):
        # If process exists, asking user what to do
        logger.warning(path + " is pointing to another running program with PID, and its not this instance!")
        if interactive:
            do_stop = process_exists_cli(pid)
        else:
            do_stop = True
        if do_stop:
            if kill_not_stop:
                logger.info("Killing the old process")
                kill_process(pid)
            else:
                try:
                    logger.info("Trying to stop the old process using systemd")
                    subprocess.call(["systemctl", "stop", "zpui"])
                except:
                    logger.info("Systemd stop failed, killing the process")
                    kill_process(pid)
                else:
                    logger.info("Stopped the process through systemd, continuing")
    logger.info("Overwriting PID file")
    create_pid(path)

if __name__ == "__main__":
    check_and_create_pid("/var/run/zpui.pid")
