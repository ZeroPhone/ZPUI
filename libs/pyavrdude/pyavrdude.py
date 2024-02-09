import os
import sys
import pty
import subprocess
import time
from select import select
from collections import OrderedDict

import heuristics

class ProHelper(object):
    """
    A helper class for keeping track of long-running processes. It launches the process
    in background, receives output from it, sends input to it. It also can emulate an
    interactive terminalm in case your process does something different when launched
    in a terminal (like showing a progress bar).
    """

    process = None

    def __init__(self, command, shell = False, use_terminal = False, output_callback = None):
        self.command = command
        self.shell = shell
        self.use_terminal = use_terminal
        if not output_callback:
            output_callback = self.print_output
        self.output_callback = output_callback

    def run(self):
        """
        Launches the process (in the background), either with an emulated
        terminal or not.
        """
        if self.use_terminal:
            self.terminal, self.s = pty.openpty()
            self.process = subprocess.Popen(self.command, stdin=self.s, stdout=self.s, stderr=self.s, shell=self.shell, close_fds=True)
        else:
            raise NotImplementedException

    def output_available(self, timeout=0.1):
        """
        Returns True if there is output from the command that
        hasn't yet been processed.
        """
        if self.use_terminal:
            return select([self.terminal], [], [], timeout)[0]
        else:
            raise NotImplementedException

    def read(self, size, timeout=None):
        """
        Reads output from the process, limited by size (with an optional
        timeout).
        """
        if self.use_terminal:
            s = select([self.terminal], [], [], timeout)[0]
            if s:
                return os.read(s[0], size)
        else:
            raise NotImplementedException

    def readall(self, timeout=0, readsize=1):
        """
        Reads all available output from the process. Timeout is 0 by default,
        meaning that function will return immediately.
        """
        output = []
        while self.output_available():
            output.append(self.read(readsize, timeout))
        return "".join(output)

    def write(self, data):
        """
        Sends input to the process.
        """
        if self.use_terminal:
            return os.write(self.terminal, data)
        else:
            raise NotImplementedException

    def run_foreground(self, delay=0.5):
        """
        This method starts the process,  blocks until it's finished
        and returns a status code. Don't use this function if you want to send
        input to the function, kill the process at a whim, or do something else
        that is not done by the output callback (unless you're running it in a
        separate thread - which might be unwarranted.
        """
        self.run()
        while self.is_ongoing():
            if callable(self.output_callback):
                self.relay_output()
            time.sleep(delay)
        return True

    def poll(self):
        """
        This function polls the process for output (and relays it into the callback),
        as well as polls whether the process is finished.
        """
        if self.process:
            self.process.poll()
            if callable(self.output_callback):
                self.relay_output()

    def relay_output(self):
        """
        This method checks if there's output waiting to be read; if there is,
        it reads all of it and sends it to the output callback.
        """
        if self.output_available():
            self.output_callback(self.readall(timeout=0))

    def print_output(self, data):
        """
        The default function used for processing output from the command.
        For now, it simply sends the data to ``sys.stdout``.
        """
        sys.stdout.write(data)
        sys.stdout.flush()

    def kill_process(self):
        """
        Terminates the process if it's running.
        """
        if not self.is_ongoing():
            return False
        return self.process.terminate()

    def get_return_code(self):
        """
        Returns the process' return code - if the process is not yet finished, return None.
        """
        return self.process.returncode

    def is_ongoing(self):
        """
        Returns whether the process is still ongoing. If the process wasn't started yet,
        return False.
        """
        if not self.process:
            return False
        self.process.poll()
        return self.process.returncode is None


class AvrdudeProcess(object):

    default_yn_response = 'n'

    def __init__(self, chip, programmer, path="avrdude", parameters=None, base_path=None):
        self.avrdude_path = path
        self.chip = chip
        self.programmer = programmer
        self.parameters = parameters if parameters else []
        self.base_path = base_path
        self.set_base_commandline()
        self.possible_fuse_changeback_responses = ['y', 'n']
        self.fuse_changeback_response = 'n'
        self.is_verifying = False

    # Run helpers

    def run_foreground(self):
        """
        Runs the AvrdudeProcess in foreground - blocking mode. You can't query
        the status, except if you're doing it from another thread. (AvrdudeProcess
        wasn't tested to be thread-safe).

        Before you call this, you'll most likely want to run ``setup_read``, ``setup_write``
        or ``setup_erase``.
        """
        self.full_output = '' # Reset full output
        self.p = ProHelper(self.command, use_terminal=True, output_callback=self.process_output)
        self.set_interactive_status({"status":"started"})
        self.p.run_foreground(delay=0)

    def run(self):
        """
        Runs the AvrdudeProcess in background - non-blocking mode. You need to call
        the ``poll`` method from time to time so that the process info and status
        are updated.

        Before you call this, you'll most likely want to run ``setup_read``, ``setup_write``
        or ``setup_erase``.
        """
        self.full_output = '' # Reset full output
        self.p = ProHelper(self.command, use_terminal=True, output_callback=self.process_output)
        self.p.run()
        self.set_interactive_status({"status":"started"})

    def poll(self):
        """
        Polls the underlying avrdude process from time to time - transferring output
        from the process' queue to the functions that process it (setting statuses
        and other things).
        """
        self.p.poll()

    # Parameter setting stuff

    def set_fuse_changeback(self, new_response='y'):
        """
        This function lets you set the default response to 'Wrong fuse values
        detected; do you want to set them back?' questions. By default, it's 'n'.
        """
        assert(new_response in self.possible_fuse_changeback_responses), "Invalid fuse changeback response: {}".format(new_response)
        self.fuse_changeback_response = new_response

    # Setup stuff

    def set_base_commandline(self):
        """
        Constructs the base commandline for avrdude - the avrdude binary path,
        programmer and chip parameters, then sets it as the command to run.
        """
        self.command = [self.avrdude_path, "-p", self.chip, "-c", self.programmer]
        self.command += self.parameters

    def get_path(self, path):
        """
        If a relative path is passed and base path is set, concatenates them;
        otherwise, returns the initial path.
        """
        if self.base_path and not os.path.isabs(path):
            return os.path.join(self.base_path, path)
        return path

    def setup_read(self, path, format="i", memtype="flash"):
        """
        Adds a "read" command to the avrdude commandline.
        """
        self.command += ['-U', '{}:r:{}:{}'.format(memtype, self.get_path(path), format)]

    def setup_write(self, path, memtype="flash", format="a"):
        """
        Adds a "write" command to the avrdude commandline.
        """
        self.command += ['-U', '{}:w:{}:{}'.format(memtype, self.get_path(path), format)]

    def setup_erase(self):
        """
        Adds an "erase" command to the avrdude commandline.
        """
        self.command += ['-e']

    # Output parsing & processing stuff

    def line_endswith_yn(self, line):
        """
        Determines if the output line ends with '[y/n]'.
        """
        return line.strip().endswith('[y/n]')

    def is_fuse_change_request_line(self, line):
        """
        Determines if the line is a "want to fix fuses?" request.
        """
        has_fuse_change_request = "Would you like this fuse to be changed back?" in line
        return has_fuse_change_request and self.line_endswith_yn(line)

    def is_progress_line(self, line):
        """
        Determines if the line is a progress output line.
        """
        rewrite_line = line.startswith("\r")
        progress_markers = ["Reading", "Writing"]
        has_progress_marker = any([line[1:len(marker)+1] == marker for marker in progress_markers])
        return rewrite_line and has_progress_marker

    def is_erasing_line(self, line):
        """
        Determines if a line is "erasing chip" line.
        """
        return "avrdude: erasing chip" in line

    def is_verifying_line(self, line):
        """
        Determines if a line is "verifying" line.
        """
        return "avrdude: " in line and "verifying" in line

    def is_verified_line(self, line):
        """
        Determines if a line is "verified" line.
        """
        return "avrdude: " in line and "verified" in line and "bytes of" in line

    def process_erasing_line(self):
        """
        Processes the "erasing chip" line. Sets the interactive status.
        """
        self.set_interactive_status({"status":"in progress", "operation":"erasing"})

    def process_verifying_line(self):
        """
        Processes the "verifying" line. Sets the internal flag that interprets the
        "reading" operation as "verifying"
        """
        self.is_verifying = True

    def process_verified_line(self):
        """
        Processes the "verified" line. Unsets the internal flag that interprets the
        "reading" operation as "verifying"
        """
        self.is_verifying = False

    def process_progress_line(self, line):
        """
        Processes the progress line. Sets the interactive status.
        """
        type, _, progress = line.strip().split('|')
        status = {"status": "in progress", "operation":type.lower().strip()}
        if status["operation"] == "reading" and self.is_verifying:
            status["operation"] = "verifying"
        progress = progress.strip()
        # We can receive a '\rWriting | [...] | 0% 0.00s ***failed;' line
        if progress.count(' ') > 1:
            percentage, time, info = progress.strip().split(' ', 2)
            if info.startswith("***failed"):
                # Failed reading, returning a 'failed' status
                self.set_interactive_status({"status":"failure"})
                return
        else:
            percentage, time = progress.strip().split(' ')
        try:
            percentage = int(percentage.strip('%'))
        except:
            print("Couldn't convert percentage value to int: {}".format(percentage))
            return
        status["progress"] = percentage
        status["time"] = time
        self.set_interactive_status(status)

    def process_output(self, output):
        """
        Processes output of the process. Is called by the ProHelper and receives a chunk
        of output which contains one or multiple lines, calls all the ``is_*_line`` and
        ``process_*_line`` methods on each line.
        """
        self.full_output += output
        lines = output.split('\n')
        for line in lines:
            if line.startswith("\r") and line.strip():
                #Progress line?
                if line.count('\r') > 1: #Line contains more than one status string
                    # Filtering through the strings and only processing the last one
                    line = '\r'+filter(None, line.split('\r'))[-1]
                if self.is_progress_line(line):
                    self.process_progress_line(line)
            elif self.is_fuse_change_request_line(line):
                self.respond_to_fuse_change_request()
            elif self.line_endswith_yn(line):
                # A line that we need to respond to, that we don't yet know about!
                self.respond_to_unknown_yn_request(line)
            elif self.is_erasing_line(line):
                self.process_erasing_line()
            elif self.is_verifying_line(line):
                self.process_verifying_line()
            elif self.is_verified_line(line):
                self.process_verified_line()
            else:
                # For now, we don't care about this line
                pass #if line.strip(): print(repr(line))

    def get_full_output(self):
        """
        Returns all the output that's been received so far - in case the avrdude
        process has finished, it's going to be the full output of the avrdude process.
        """
        return self.full_output

    # Automatic responses

    def respond_to_fuse_change_request(self):
        """
        Responds to the fuse change request with the set changeback response
        (by default, 'n').
        """
        self.p.write(self.fuse_changeback_response+'\n')
        self.set_interactive_status({"status":"in progress", "operation":"restoring fuses"})

    def respond_to_unknown_yn_request(line):
        """
        Responds to an unknown '[y/n]' request (which we need to respond to, otherwise,
        it'd block the process indefinitely.
        """
        self.p.write(self.default_yn_response+'\n')

    # Status functions

    def set_interactive_status(self, status):
        """
        An internal method to set interactive status, which the user can then query
        using the ``get_interactive_status`` method.
        """
        self.interactive_status = status

    def get_interactive_status(self):
        """
        A short version of status - in case you want to make an UI which queries the
        AvrdudeProcess running in background.

        Possible return values:
        {"status":"not started"}
        {"status":"started"}
        {"status":"success"}
        {"status":"failure"}
        {"status":"in progress", "operation":"erasing"}
        {"status":"in progress", "operation":"reading", "progress":13, "time":"0.00s"}
        {"status":"in progress", "operation":"writing", "progress":50, "time":"20.13s"}
        {"status":"in progress", "operation":"verifying", "progress":99, "time":"9.52s"}
        {"status":"in progress", "operation":"restoring fuses"}

        For anything more verbose, you'll want to use heuristics on the output of
        the ``get_status`` method.
        """
        if not self.p.process:
            return {"status":"not started"}
        if not self.p.is_ongoing():
            return {"status":"success"} if self.p.get_return_code() == 0 else {"status":"failure"}
        return self.interactive_status

    def get_status(self):
        """
        Gets full status of a process, which can then be passed to heuristics
        processing functions. For UI usage, consider using ``get_interactive_status``,
        which will contain realtime data about the process (including progress
        of currently ongoing operations).
        """
        status = {"result":None, "exitcode":0, "errors":[], "output":[], "full_output":None, "other":[]}
        status["commandline"] = self.command
        if self.p.is_ongoing():
            status["exitcode"] = None
            status["result"] = "ongoing"
        else:
            status["exitcode"] = self.p.get_return_code()
            if status["exitcode"] == 0:
                status["result"] = "success"
            else:
                status["result"] = "failed"
        status["full_output"] = self.get_full_output()
        status = parse_output_into_status(status)
        return status


def get_parts():
    try:
        output = subprocess.check_output(["avrdude", "-p", "?"], stderr = subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        output = e.output
    if isinstance(output, bytes): output = output.decode("ascii")
    lines = filter(None, [line.strip() for line in  output.split(os.linesep)])
    entries = OrderedDict()
    for line in lines:
        if "=" in line and len(line.split("=")) == 2:
            alias, name = (entry.strip() for entry in line.split("="))
            if " " not in name:
                entries[alias] = name
    return entries

def get_programmers():
    try:
        output = subprocess.check_output(["avrdude", "-c", "?"], stderr = subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        output = e.output
    if isinstance(output, bytes): output = output.decode("ascii")
    lines = filter(None, [line.strip() for line in  output.split(os.linesep)])
    entries = OrderedDict()
    for line in lines:
        if "=" in line and len(line.split("=")) == 2:
            alias, name = (entry.strip() for entry in line.split("="))
            entries[alias] = name
    return entries

def parse_output_into_status(status):
    output = status["full_output"]
    lines = [line.strip() for line in output.split(os.linesep)]
    lines = filter(None, lines)
    start_marker = "avrdude: "
    avrdude_lines = []
    for line in lines:
        if line.startswith(start_marker):
            avrdude_lines.append(line[len(start_marker):])
        else:
            status["other"].append(line)
    error_marker = "error: "
    for line in avrdude_lines:
        if line.startswith(error_marker):
            status["errors"].append(line[len(error_marker):])
        else:
            status["output"].append(line)
    return status

def detect_chip(part_name, programmer_name, *args):
    status = {"result":None, "exitcode":0, "errors":[], "output":[], "full_output":None, "other":[]}
    commandline = ["avrdude", "-p", part_name, "-c", programmer_name]
    commandline += args
    status["commandline"] = commandline
    try:
        output = subprocess.check_output(commandline, stderr = subprocess.STDOUT)
        status["result"] = "success"
        status["exitcode"] = 0
    except subprocess.CalledProcessError as e:
        output = e.output
        status["result"] = "failed"
        status["exitcode"] = e.returncode
    if isinstance(output, bytes): output = output.decode("ascii")
    status["full_output"] = output
    status = parse_output_into_status(status)
    return status            

def erase(part_name, programmer_name):
    #TODO: parse parameters?
    #TODO: safety checks?
    p = AvrdudeProcess(part_name, programmer_name)
    p.setup_erase()
    p.run()
    return p

def write_flash(part_name, programmer_name, path):
    #TODO: parse parameters?
    #TODO: safety checks?
    p = AvrdudeProcess(part_name, programmer_name)
    p.setup_write(path)
    p.run()
    return p

def read_flash(part_name, programmer_name, path):
    #TODO: parse parameters?
    #TODO: safety checks?
    p = AvrdudeProcess(part_name, programmer_name)
    p.setup_read(path)
    p.run()
    return p

def wif(filename, output):
    with open(filename, 'a') as f:
        f.write(output)

if __name__ == "__main__":
    status = detect_chip("m328p", "usbasp")
    print(status)
    p = AvrdudeProcess('m328p', 'usbasp', parameters=['-B', '20'])
    #p.setup_read('text.hex')
    p.setup_write('/root/atmega/arduino-1.8.5/hardware/arduino/avr/bootloaders/optiboot/optiboot_atmega8.hex')
    p.run()
    status = p.get_interactive_status()
    print(status)
    while p.p.is_ongoing():
        p.poll()
        new_status = p.get_interactive_status()
        if new_status != status:
            status = new_status
            print(status)
    print(heuristics.get_human_readable_status(p.get_status()))
