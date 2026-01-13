import os
import sys
from zpui_lib.helpers import ProHelper, setup_logger

logger = setup_logger(__name__, "info")

class MTKDownloadProcess(object):
    state = "not_started"
    output = ""
    returncode = None

    def __init__(self, port, fw_dir, path="mtkdownload", callback=None):
        self.mtkdownload_path = path
        self.port = port
        self.callback = callback
        self.fw_dir = fw_dir
        self.output = []

    def mtkdownload_is_available(self):
        try:
            p = ProHelper([self.mtkdownload_path], use_terminal=True, output_callback=None)
            p.run_in_foreground()
            if p.get_return_code() != 1:
                return False
            return True
        except OSError:
            False

    def gen_commandline(self, format_fat="Y"):
        return [self.mtkdownload_path, self.port, "ROM_VIVA", format_fat]

    def write_image(self, reset_cb=None):
        self.state = "not_started"
        self.output = ""
        commandline = self.gen_commandline()
        p = ProHelper(commandline, cwd=self.fw_dir, use_terminal=True, output_callback=self.process_output)
        if callable(reset_cb):
            reset_cb()
        p.run()
        self.state = "started"
        while p.is_ongoing():
            p.poll(read_type="readall_or_until", read_kw={"until":"\r"})
            if not p.is_ongoing():
                rc = p.get_return_code()
                self.returncode = rc
                if rc != 0:
                    self.state = "failed"
                else:
                    self.state = "finished"
            if callable(self.callback):
                self.callback(self.get_state())
        if callable(reset_cb):
            reset_cb()

    def process_output(self, output):
        sys.stdout.flush()
        self.output += output
        if self.is_rom_progress_output(output):
            self.process_rom_progress_output(output)
        elif self.is_detected_chip_output(output):
            self.process_detected_chip_output(output)
        else:
            logger.info("Yet unrecognized input: {}".format( repr(output) ))

    def is_detected_chip_output(self, output):
        # '\t52' repeated a lot of times
        return '\t52'*10 in output

    def process_detected_chip_output(self, output):
        self.state = "processing"

    def is_rom_progress_output(self, output):
        # example: 'Rom 87%\t 1672832 bytes sent   \r'
        return output.startswith("Rom") and output.endswith('\r')

    def process_rom_progress_output(self, output):
        # example: 'Rom 87%\t 1672832 bytes sent   \r'
        self.state = "flashing"
        try:
            progress = output.split(' ', 1)[1].split('\t', 1)[0]
            self.progress = int(progress.strip('%'))
        except:
            logger.exception("can't parse progress string: {}".format(repr(output)))

    def get_state(self):
        s_d = {"state":self.state, "output":self.output}
        if self.state == "failed":
            s_d["returncode"] = self.returncode
        elif self.state == "flashing":
            s_d["progress"] = self.progress
        return s_d

def collect_fw_folders(base_path, key="SIM800", check_cfg=True, requirements=["ROM", "ROM_VIVA", "VIVA"]):
    logger.info("Collecting \"{}\" firmware from {}".format(key, base_path))
    unsorted_paths = []
    for path in os.listdir(base_path):
        full_path = os.path.join(base_path, path)
        if os.path.isdir(full_path):
            if key not in path:
                logger.debug("{} doesn't have \"{}\" key in it, continuing".format(path, key))
                continue
            fw_files = os.listdir(full_path)
            version = None
            if "sim_fw_zp_version" in fw_files:
                with open(os.path.join(full_path, "sim_fw_zp_version")) as f:
                    version = f.read().strip()
            if check_cfg and not "{}.cfg".format(path) in fw_files:
                logger.info("{} doesn't have CFG, continuing".format(path))
                continue
            if not all([req in fw_files for req in requirements]):
                logger.info("{} doesn't have one of the requirements, continuing".format(path))
                continue
            unsorted_paths.append([version, full_path])
    logger.info(unsorted_paths)
    paths = [path for v, path in reversed(sorted(unsorted_paths))]
    return paths
