import os
import signal
from actions import FirstBootAction
from subprocess import check_output, STDOUT, CalledProcessError
from time import sleep
import json

try:
    import httplib
except:
    import http.client as httplib

from ui import Menu, PrettyPrinter, DialogBox, ProgressBar, Listbox, UniversalInput, HelpOverlay
from helpers import setup_logger, read_or_create_config, save_config_method_gen, local_path_gen

local_path = local_path_gen(__name__)

import bugreport_ui
import logging_ui
import about

menu_name = "Settings"
logger = setup_logger(__name__, "info")

class GitInterface(object):

    @classmethod
    def git_available(cls):
        try:
            cls.command("--help")
        except OSError:
            return False
        return True

    @staticmethod
    def command(command):
        commandline = "git {}".format(command)
        logger.debug("Executing: {}".format(commandline))
        return check_output(commandline, shell=True, stderr=STDOUT)

    @classmethod
    def get_head_for_branch(cls, branch):
        output = cls.command("rev-parse {}".format(branch)).strip()
        return output

    @classmethod
    def get_origin_url(cls):
        try:
            return cls.command("remote get-url origin").strip()
        except CalledProcessError: #Git v2.1 does not support get-url
            return cls.command("config remote.origin.url").strip()

    @classmethod
    def set_origin_url(cls, url):
        return cls.command("remote set-url origin {}".format(url)).strip()

    @classmethod
    def get_current_branch(cls):
        return cls.get_head_for_branch("--abbrev-ref HEAD").strip()

    @classmethod
    def checkout(cls, reference):
        return cls.command("checkout {}".format(reference))

    @classmethod
    def pull(cls, source = "origin", branch = "master", opts="--no-edit"):
        try:
            return cls.command("pull {2} {0} {1}".format(source, branch, opts))
        except CalledProcessError as e:
            lines = iter(e.output.split('\n'))
            logger.debug("Parsing output")
            marker1 = "following untracked working tree files would be overwritten by merge"
            marker2 = "local changes to the following files would be overwritten by merge"
            for line in lines:
                logger.debug(repr(line))
                if marker1 in line or marker2 in line:
                    logger.info("Found interfering files!")
                    line = next(lines)
                    while line.startswith('\t'):
                        line = line.strip()
                        if not line.endswith('/'):
                            try:
                                logger.info("Removing interfering file: {}".format(line))
                                os.remove(line)
                            except OSError:
                                logger.warning("Couldn't remove an interfering file {} while pulling!".format(line))
                        line = next(lines)
            return cls.command("pull {2} {0} {1}".format(source, branch, opts))


class UpdateUnnecessary(Exception):
    pass


class GenericUpdater(object):
    steps = []
    progressbar_messages = {}
    failed_messages = {}

    def run_step(self, step_name):
        logger.info("Running update step: '{}'".format(step_name))
        getattr(self, "do_" + step_name)()
        logger.debug("Update step '{}' completed!".format(step_name))

    def revert_step(self, step_name):
        if hasattr(self, "revert_" + step_name):
            logger.info("Reverting update step: '{}'".format(step_name))
            getattr(self, "revert_" + step_name)()
            logger.debug("Update step '{}' reverted!".format(step_name))
        else:
            logger.debug("Can't revert step {} - no reverter available.".format(step_name))

    def update_on_firstboot(self):
        choice = DialogBox("yn", i, o, message="Update ZPUI?", name="ZPUI update app firstboot dialog").activate()
        if not choice:
            return None
        return self.update(suggest_restart=False)

    def update(self, suggest_restart=True, skip_steps=None):
        logger.info("Starting update process")
        pb = ProgressBar(i, o, message="Updating ZPUI")
        pb.run_in_background()
        progress_per_step = 100 / len(self.steps)
        skip_steps = skip_steps if skip_steps else []

        completed_steps = []
        try:
            for step in self.steps:
                if step in skip_steps:
                    continue
                pb.set_message(self.progressbar_messages.get(step, "Loading..."))
                sleep(0.5)  # The user needs some time to read the message
                self.run_step(step)
                completed_steps.append(step)
                pb.progress += progress_per_step
        except UpdateUnnecessary:
            logger.info("Update is unnecessary!")
            pb.stop()
            PrettyPrinter("ZPUI already up-to-date!", i, o, 2)
            return True
        except:
            # Name of the failed step is contained in `step` variable
            failed_step = step
            logger.exception("Failed on step {}".format(failed_step))
            failed_message = self.failed_messages.get(failed_step, "Failed on step '{}'".format(failed_step))
            with pb.paused:
                PrettyPrinter(failed_message, i, o, 2)
                pb.set_message("Reverting update")
            try:
                logger.info("Reverting the failed step: {}".format(failed_step))
                self.revert_step(failed_step)
            except:
                logger.exception("Can't revert failed step {}".format(failed_step))
                with pb.paused:
                    PrettyPrinter("Can't revert failed step '{}'".format(step), i, o, 2)
            logger.info("Reverting the previous steps")
            for step in completed_steps:
                try:
                    self.revert_step(step)
                except:
                    logger.exception("Failed to revert step {}".format(failed_step))
                    with pb.paused:
                        PrettyPrinter("Failed to revert step '{}'".format(step), i, o, 2)
                pb.progress -= progress_per_step
            sleep(1) # Needed here so that 1) the progressbar goes to 0 2) run_in_background launches the thread before the final stop() call
            #TODO: add a way to pause the Refresher
            pb.stop()
            logger.info("Update failed")
            PrettyPrinter("Update failed, try again later?", i, o, 3)
            return False
        else:
            logger.info("Update successful!")
            sleep(0.5)  # showing the completed progressbar
            pb.stop()
            PrettyPrinter("Update successful!", i, o, 3)
            if suggest_restart:
                self.suggest_restart()
            return True

    def suggest_restart(self):
        needs_restart = DialogBox('yn', i, o, message="Restart ZPUI?").activate()
        if needs_restart:
            os.kill(os.getpid(), signal.SIGTERM)


class GitUpdater(GenericUpdater):
    branch = "master"

    steps = ["check_connection", "check_git", "set_url", "check_revisions", "pull", "install_requirements", "pretest_migrations", "tests"]
    progressbar_messages = {
        "check_connection": "Connection check",
        "check_git": "Running git",
        "set_url": "Setting URL",
        "check_revisions": "Comparing code",
        "pull": "Fetching code",
        "install_requirements": "Installing packages",
        "pretest_migrations": "Running migrations",
        "tests": "Running tests"
    }
    failed_messages = {
        "check_connection": "No Internet connection!",
        "check_git": "Git binary not found!",
        "check_revisions": "Exception while comparing revisions!",
        "set_url": "Can't set URL!",
        "pull": "Couldn't get new code!",
        "install_requirements": "Failed to install new packages!",
        "pretest_migrations": "Failed to run migrations!",
        "tests": "Tests failed!"
    }

    config_filename = "git_updater.json"
    safe_branches = ["master", "staging", "devel"]
    # Forming the default config
    default_config = '{"url":"https://github.com/ZeroPhone/ZPUI", "branches":[]}'
    json_config = json.loads(default_config)
    json_config["branches"] = safe_branches
    default_config = json.dumps(json_config)

    def __init__(self, check_revisions=True):
        GenericUpdater.__init__(self)
        self.check_revisions = check_revisions
        self.config = read_or_create_config(local_path(self.config_filename), self.default_config, "Git updater")
        self.save_config = save_config_method_gen(self, local_path(self.config_filename))

    def do_check_git(self):
        if not GitInterface.git_available():
            logger.exception("Couldn't execute git - not found?")
            raise OSError()

    def do_check_revisions(self):
        GitInterface.command("fetch")
        current_branch_name = GitInterface.get_current_branch()
        current_revision = GitInterface.get_head_for_branch(current_branch_name)
        remote_revision = GitInterface.get_head_for_branch("origin/"+current_branch_name)
        if self.check_revisions and current_revision == remote_revision:
            raise UpdateUnnecessary
        else:
            self.previous_revision = current_revision

    def do_set_url(self):
        self.previous_url = GitInterface.get_origin_url()
        GitInterface.set_origin_url(self.config["url"])

    def do_check_connection(self):
        conn = httplib.HTTPConnection("github.com", timeout=10)
        try:
            conn.request("HEAD", "/")
        except:
            raise
        finally:
            conn.close()

    def do_install_requirements(self):
        output = check_output(["pip", "install", "-r", "requirements.txt"])
        logger.debug("pip output:")
        logger.debug(output)

    def do_pull(self):
        current_branch_name = GitInterface.get_current_branch()
        GitInterface.pull(branch = current_branch_name)

    def change_origin_url(self):
        original_url = self.config["url"]
        url = UniversalInput(i, o, message="URL:", value=original_url).activate()
        if url:
            self.config["url"] = url
            self.save_config()
            PrettyPrinter("Saved new URL!", i, o)

    def settings(self):
        mc = [
        ["Select branch", self.pick_branch],
        ["Change URL", self.change_origin_url]]
        Menu(mc, i, o, name="Git updater settings menu").activate()

    def do_pretest_migrations(self):
        import pretest_migration
        pretest_migration.main()

    def revert_pretest_migrations(self):
        import pretest_migration
        if hasattr(pretest_migration, 'revert'):
            pretest_migration.revert()

    def do_tests(self):
        with open('test_commandline', 'r') as f:
            commandline = f.readline().strip()
        try:
            output = check_output(commandline.split(" "))
            logger.debug("pytest output:")
            logger.debug(output)
        except CalledProcessError as e:
            logger.warning("pytest output:")
            logger.warning(e.output)
            raise

    def revert_pull(self):
        # do_check_revisions already ran, we now have the previous revision's
        # commit hash in self.previous_revision
        GitInterface.command("reset --hard {}".format(self.previous_revision))
        # requirements.txt now contains old requirements, let's install them back
        self.do_install_requirements()

    def revert_set_url(self):
        # do_set_url already ran, we now have the previous URL in self.previous_url
        # or do we?
        if hasattr(self, 'previous_url'):
            GitInterface.set_origin_url(self.previous_url)

    def pick_branch(self):
        #TODO: allow adding branches dynamically instead of having a whitelist
        lc = [[branch_name] for branch_name in self.config["branches"]]
        branch = Listbox(lc, i, o, name="Git updater branch selection listbox").activate()
        if branch:
            try:
                GitInterface.checkout(branch)
                self.check_revisions = False
                updated = self.update()
                self.check_revisions = True
            except:
                PrettyPrinter("Couldn't check out the {} branch! Try resolving the conflict through the command-line.".format(branch), i, o, 3)
            else:
                PrettyPrinter("Now on {} branch!".format(branch), i, o, 2)
                self.suggest_restart()


i = None  # Input device
o = None  # Output device
git_updater = None
context = None
update_zpui_fba = None

def set_context(c):
    global context
    context = c
    context.register_firstboot_action(bugreport_ui.autosend_optin_fba)
    context.register_firstboot_action(update_zpui_fba)

def init_app(input, output):
    global i, o, git_updater, update_zpui_fba
    i = input
    o = output
    logging_ui.i = i
    logging_ui.o = o
    bugreport_ui.i = i
    bugreport_ui.o = o
    bugreport_ui.git_if = GitInterface
    about.i = i
    about.o = o
    about.git_if = GitInterface
    git_updater = GitUpdater()
    update_zpui_fba = FirstBootAction("update_zpui", git_updater.update_on_firstboot, depends=["check_connectivity"])

def callback():
    c = [["Update ZPUI", git_updater.update, git_updater.settings],
         ["Bugreport", bugreport_ui.main_menu],
         ["Logging settings", logging_ui.config_logging],
         ["About", about.about]]
    menu = Menu(c, i, o, "ZPUI settings menu")
    help_text = "Press RIGHT on \"Update ZPUI\" to change OTA update settings (branch or git URL to use)"
    HelpOverlay(help_text).apply_to(menu)
    menu.activate()
