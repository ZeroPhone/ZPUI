from __future__ import division

import os
import shlex
import shutil
import subprocess
import tempfile
from time import sleep

from apps import ZeroApp
from helpers.general import ZPUI_INSTALL_DIR
from helpers.logger import setup_logger
from ui import Menu, DialogBox, Printer, ProgressBar

logger = setup_logger(__name__, "info")


class ZpuiUpdaterApp(ZeroApp):
    def __init__(self, i, o):
        super(ZpuiUpdaterApp, self).__init__(i, o)
        self.menu_name = "Update ZPUI"
        self.menu = Menu(
            [
                ["Update ZPUI", self.update_zpui],
                ["Update ZPUI(devel)", self.update_zpui_devel]
            ],
            i,
            o,
            "ZPUI settings menu"
        )
        self.steps = []

    def on_start(self):
        super(ZpuiUpdaterApp, self).on_start()
        self.menu.activate()

    def update_zpui(self):
        self.start_update(branch="master")

    def update_zpui_devel(self):
        if DialogBox("yn", self.i, self.o, message="You sure ?").activate():
            self.start_update(branch="devel")
        else:
            Printer("Update canceled", self.i, self.o)

    def start_update(self, branch):
        self.create_steps(branch)
        finished_steps = []
        with ProgressBar(self.i, self.o) as bar:
            for step in self.steps:
                try:
                    bar.message = step.name
                    step.do()
                    finished_steps.append(step)
                    bar.progress = len(finished_steps) / len(self.steps)
                    bar.refresh()
                    sleep(0.5)  # so the user has time to read what happens
                except Exception as e:
                    if DialogBox("yn", self.i, self.o,
                                 message="'{}'failed\ncancel update?".format(step.name)).activate():
                        self.rollback_update(bar, e, finished_steps, step)
                        return -1
                    else:
                        pass

    def rollback_update(self, bar, e, finished_steps, step):
        logger.error("Error updating step '{}'".format(step.name))
        logger.exception(e)
        Printer([step.name, 'update failed'], self.i, self.o)
        bar.message = "reverting"
        for i, passed in enumerate(finished_steps):
            passed.undo()
            bar.progress = (len(finished_steps) - i) / len(self.steps)
            bar.refresh()
            sleep(0.5)

    def create_steps(self, branch="master"):
        tmp_dir = tempfile.mkdtemp(prefix='zpui')
        os.chmod(tmp_dir, 0o777)
        old_cwd = os.getcwd()
        change_cwd = UpdateStep("opening tmp dir", lambda: os.chdir(tmp_dir), lambda: os.chdir(old_cwd))
        self.steps.append(change_cwd)

        git_copy = UpdateStep(
            "copying repo",
            "git clone {src_dir} {dir}/".format(src_dir=ZPUI_INSTALL_DIR, dir=tmp_dir, branch=branch)
        )
        self.steps.append(git_copy)

        git_pull = UpdateStep(
            "pulling git",
            "git pull origin {branch} --ff-only".format(dir=tmp_dir, branch=branch)
        )
        self.steps.append(git_pull)

        pip_install = UpdateStep("installing deps",
                                 "pip2 install -r requirements.txt",
                                 "pip2 install -r {src_dir}requirements.txt".format(src_dir=ZPUI_INSTALL_DIR)
                                 )
        self.steps.append(pip_install)

        run_tests = UpdateStep(
            "running tests",
            "python2 -B -m pytest --doctest-modules -v --doctest-ignore-import-errors --ignore=output/drivers "
            "--ignore=input/drivers --ignore=apps/hardware_apps/status/ --ignore=apps/example_apps/fire_detector "
            "--ignore=apps/test_hardware",
            accepted_return_code=0
        )
        self.steps.append(run_tests)

        change_cwd_back = UpdateStep("change cwd back", lambda: os.chdir(old_cwd))
        self.steps.append(change_cwd_back)

        copy_update_files = UpdateStep(
            "patching ZPUI",
            "rsync -av --delete {tmp_dir} --exclude='*.pyc' {dst_dir}".format(tmp_dir=tmp_dir, dst_dir=ZPUI_INSTALL_DIR)
        )
        self.steps.append(copy_update_files)

        restart_service = UpdateStep(
            "restarting zpui",
            "systemctl restart zpui.service"
        )
        self.steps.append(restart_service)

        clean_tmp_dir = UpdateStep("cleaning tmp dir", lambda: shutil.rmtree(tmp_dir))
        self.steps.append(clean_tmp_dir)


class UpdateStep(object):
    def __init__(self, name, do=None, undo=None, accepted_return_code=None):
        self.accepted_return_code = accepted_return_code
        self.name = name
        self._do = do
        self._undo = undo
        self.return_value = None

    def do(self):
        if not self._do:
            return
        logger.debug("running '{}'".format(self.name))
        if isinstance(self._do, basestring):
            print(shlex.split(self._do))
            self.return_value = subprocess.call(shlex.split(self._do))
        else:
            self.return_value = self._do()
        logger.debug("ran '{}' with return value '{}'".format(self.name, self.return_value))
        if self.accepted_return_code is not None:
            if not self.return_value == self.accepted_return_code:
                raise Exception("'{}' failed".format(self.name))
        return self.return_value

    def undo(self):
        if not self._undo:
            logger.warning("no undo method for '{}'".format(self.name))
        else:
            logger.debug("Undoing '{}'".format(self.name))
            self._undo()
