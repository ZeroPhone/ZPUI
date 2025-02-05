import os
import sys
import pty
import threading
import subprocess
import time
from select import select

class ProHelper(object):
    """
    A helper class for keeping track of long-running processes. It launches the process
    in background, receives output from it, sends input to it. It also can emulate an
    interactive terminalm in case your process does something different when launched
    in a terminal (like showing a progress bar).
    """

    process = None

    def __init__(self, command, shell = False, use_terminal = True, output_callback = None, cwd = None, popen_kwargs = None):
        self.command = command
        self.shell = shell
        self.cwd = cwd
        self.use_terminal = use_terminal
        self.output_callback = output_callback
        self.popen_kwargs = popen_kwargs if popen_kwargs else {}
        if self.output_callback == 'print':
            self.output_callback = self.print_output

    def run(self):
        """
        Launches the process (in the background), either with an emulated
        terminal or not.
        """
        if self.use_terminal:
            self.terminal, self.s = pty.openpty()
            self.process = subprocess.Popen(self.command, stdin=self.s, stdout=self.s, stderr=self.s, shell=self.shell, cwd=self.cwd, close_fds=True, **self.popen_kwargs)
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

    def readall_or_until(self, timeout=0, readsize=1, until=None):
        """
        Reads all available output from the process, or until a character is encountered.
        Timeout is 0 by default, meaning that function will return immediately.
        """
        output = []
        while self.output_available():
            data = self.read(readsize, timeout)
            output.append(data)
            if data == until:
                break
        return "".join(output)

    def readall(self, timeout=0, readsize=1):
        """
        Reads all available output from the process. Timeout is 0 by default,
        meaning that function will return immediately (unless output is a constant
        stream of data, in which case it's best if you use ``readall_or_until``.
        """
        output = []
        while self.output_available():
            data = self.read(readsize, timeout)
            output.append(data)
        return "".join(output)

    def write(self, data):
        """
        Sends input to the process.
        """
        if self.use_terminal:
            return os.write(self.terminal, data)
        else:
            raise NotImplementedException

    def run_in_foreground(self, delay=0.5):
        """
        This method starts the process,  blocks until it's finished
        and returns a status code. Don't use this function if you want to send
        input to the function, kill the process at a whim, or do something else
        that is not done by the output callback (unless you're running it in a
        separate thread - which might be unwarranted).
        """
        self.run()
        while self.is_ongoing():
            if callable(self.output_callback):
                self.relay_output()
            time.sleep(delay)
        return True

    def run_in_background(self, delay=0.5, thread_name=None):
        """
        Runs the ``run_in_foreground`` method in a separate thread.
        Can set the thread name, can also pass the ``delay`` argument.
        """
        self.thread = threading.Thread(target=self.run_in_foreground, kwargs={"delay":delay})
        self.thread.daemon = True
        self.thread.start()

    def poll(self, **read_kw):
        """
        This function polls the process for output (and relays it into the callback),
        as well as polls whether the process is finished.
        """
        if self.process:
            self.process.poll()
            if callable(self.output_callback):
                self.relay_output(**read_kw)

    def relay_output(self, read_type="readall", read_kw={}):
        """
        This method checks if there's output waiting to be read; if there is,
        it reads all of it and sends it to the output callback.
        """
        if self.output_available():
            read = getattr(self, read_type)
            output = read(timeout=0, **read_kw)
            self.output_callback(output)

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

    def dump_info(self):
        self.poll()
        ongoing = self.is_ongoing()
        info = {"command":self.command, "is_ongoing":ongoing, "return_code":None,
                "cwd":self.cwd, "shell":self.shell, "use_terminal":self.use_terminal,
                "output_callback":str(self.output_callback),
                "popen_kwargs":self.popen_kwargs }
        if not ongoing:
            info["return_code"] = self.get_return_code()
        return info


import unittest

class TestProHelper(unittest.TestCase):
    """Tests the ProHelper"""

    def test_constructor(self):
        ph = ProHelper("python")
        self.assertIsNotNone(ph)

    def test_run_foreground(self):
        ph = ProHelper(["echo", "hello"], use_terminal=True)
        ph.run_in_foreground()
        assert(ph.output_available())
        output = ph.readall(timeout=5, readsize=1024)
        assert(output.strip() == "hello")
        assert(ph.get_return_code() == 0)

    def test_exit_code_1(self):
        ph = ProHelper("false", use_terminal=True)
        ph.run_in_foreground()
        assert(ph.get_return_code() == 1)

    def test_dump_info(self):
        ph = ProHelper("false", use_terminal=True)
        ph.run_in_foreground()
        info = ph.dump_info()
        assert(info["return_code"] == 1)
        assert(info["is_ongoing"] == False)

    def test_launch_kill(self):
        ph = ProHelper("python", use_terminal=True, output_callback=lambda *a, **k: True)
        ph.run()
        ph.poll()
        assert(ph.is_ongoing())
        ph.kill_process()
        ph.poll()
        assert(not ph.is_ongoing())

    @unittest.skip("No idea how to implement this properly without making test running even more long")
    def test_input(self):
        ph = ProHelper(["python", "-c", "raw_input('hello')"], use_terminal=True)
        ph.run()
        ph.poll()
        assert(ph.is_ongoing())
        ph.write('\n')
        output = ph.readall(timeout=5, readsize=1024)
        ph.poll()
        ph.read(1)
        print(repr(output))
        assert(not ph.is_ongoing())
        assert(output.strip() == "hello")


if __name__ == '__main__':
    import sys
    if sys.argv[-1] != "play":
        unittest.main()
