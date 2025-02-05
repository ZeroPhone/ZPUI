from time import sleep
import traceback
import shlex
import re

from helpers import ProHelper, setup_logger

from wpa_cli import WPAException

logger = setup_logger(__name__, "debug")

class WPAOException(WPAException):
    def __init__(self, reason, info):
        self.reason = reason
        self.info = info
        message = "'wpa_cli' output {}: {}".format(self.reason, self.info)
        Exception.__init__(self, message)

class WpaMonitor():

    started = True
    event_cb = None
    default_path = "wpa_cli"
    status_storage_len_limit = 500
    special_codes = {"CTRL-EVENT-CONNECTED":"process_ctrl_event_connected"}

    def __init__(self, path=None):
        if path:
            self.default_path = path
        self.flush_status()

    def start(self, interface=None, event_cb=None):
        self.interface = interface
        self.started = True
        args = [self.default_path]
        if interface:
            args += ["-i"+interface]
        self.event_cb = event_cb
        self.p = ProHelper(args, output_callback=self.process_output)
        #self.p.run()
        self.p.run_in_background()

    def stop(self):
        if not self.started:
            return
        #self.p.write("q\n")
        self.event_cb = None
        self.started = False
        self.p.kill_process()

    def process_output(self, output):
        #print(repr(output))
        lines = output.split('\r\n')
        #print(lines)
        for line in lines:
          try:
            prompt_marker = "> "
            if line.startswith(prompt_marker):
                line = line[len(prompt_marker):]
            if not line: break
            line = line.lstrip('\r')
            if line.startswith("<"):
                try:
                    self.parse_msg(line)
                except:
                    traceback.print_exc()
                    raise WPAOException("can't parse", line)
            else:
                print(repr(line))
          except:
              logger.exception("Exception while processing output from wpa_cli")

    def parse_msg(self, message):
        num, message = message.lstrip("<").split(">", 1)
        status = {"n":int(num), "msg":message, "data":{}, "code":""}
        if message.startswith("CTRL"):
            parts = shlex.split(message, " ")
            code = parts[0]
            if code in self.special_codes.keys():
                status["code"] = code
                process_f_name = self.special_codes[code]
                process_f = getattr(self, process_f_name)
                status = process_f(status)
            else:
                args = parts[1:]
                data = {}
                for arg in args:
                    key, value = arg.split("=", 1)
                    data[key] = value
                status["code"] = code
                status["data"] = data
        else:
            pass # We can't yet parse this message
        if status["code"] and not status["code"].startswith("CTRL-EVENT-SCAN") \
          and not status["code"].startswith("CTRL-EVENT-REGDOM"):
            print(status)
        self.add_status(status)
        if self.event_cb:
          try:
            self.event_cb(status)
          except:
            logger.exception("Calling event_cb for if {} raised an exception".format(self.interface))

    def process_ctrl_event_connected(self, status):
        msg = status["msg"]
        info_str, data_str = msg.rsplit("[", 1)
        # processing info_str = something like "CTRL-EVENT-CONNECTED - Connection to 64:66:b3:54:5a:d8 completed "
        # using a regex to find the bssid
        # from https://stackoverflow.com/questions/26891833/python-regex-extract-mac-addresses-from-string/26892371
        p = re.compile(ur'(?:[0-9a-fA-F]:?){12}')
        results = re.findall(p, info_str)
        # let's be a bit paranoid - what if the regex doesn't actually find the bssid>?
        if not results:
            bssid = None
        else:
            # filtering
            results = [result for result in results if result.count(":") == 5]
            bssid = results[0]
            if len(results) > 1:
                # found more than one 0_0
                logger.warning("Status {} message contains more than one BSSID-like thing: {}".format(status, results))
        # processing data_str = something like "id=1 id_str=]"
        data_str = data_str.rstrip("]")
        data_parts = data_str.split(" ")
        # ['id=0', 'id_str=']
        data = dict([part.split("=", 1) for part in data_parts])
        # {'id': '0', 'id_str': ''}
        if "id" in data:
            data["id"] = int(data["id"])
        data["bssid"] = bssid
        status["data"] = data
        return status

    def flush_status(self):
        self.status_storage = []

    def add_status(self, status):
        self.status_storage.append(status)
        # avoid taking up too much memory
        if len(self.status_storage) > self.status_storage_len_limit:
            self.status_storage = self.status_storage[-self.status_storage_len_limit:]

    def get_status(self):
        if len(self.status_storage) > 0:
            return self.status_storage[0]
        return None

    def pop_status(self):
        try:
            status = self.status_storage.pop(0)
        except IndexError:
            return None
        else:
            return status

"""mon = None
def main(interface='wlx40a5ef071806'):
    global mon
    mon = WpaMonitor()
    mon.start(interface=interface)

if __name__ == "__main__":
    main()
"""
