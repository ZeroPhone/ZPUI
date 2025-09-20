import os
import json
import signal
from time import sleep
from subprocess import check_output, STDOUT, CalledProcessError

from pkg_resources import packaging # for pip version check

try:
    import httplib
except:
    import http.client as httplib

from zpui_lib.ui import Menu, PrettyPrinter, DialogBox, ProgressBar, Listbox, UniversalInput, HelpOverlay, TextReader, Zone, crop, replace_color, open_image
from zpui_lib.helpers import setup_logger, read_or_create_config, save_config_method_gen, local_path_gen, get_safe_file_backup_path, BackgroundRunner, BooleanEvent
from zpui_lib.actions import FirstBootAction
from zpui_lib.apps import ZeroApp

local_path = local_path_gen(__name__)

import bugreport_ui
import logging_ui
import about

logger = setup_logger(__name__, "info")

i = None
o = None

class GitInterface(object):

    moved_files = []

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
        output = check_output(commandline, shell=True, stderr=STDOUT)
        if isinstance(output, bytes): output = output.decode("utf-8")
        return output

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
    def get_diff(cls, start, end):
        return cls.command("log {}..{} --oneline".format(start, end)).strip()

    @classmethod
    def checkout(cls, reference):
        return cls.command("checkout {}".format(reference))

    @classmethod
    def pull(cls, source = "origin", branch = "master", opts="--no-edit"):
        try:
            return cls.command("pull {2} {0} {1}".format(source, branch, opts))
        except CalledProcessError as e:
            interfering_files = False
            output = e.output
            if isinstance(output, bytes): output = output.decode("utf-8")
            lines = iter(output.split('\n'))
            logger.debug("Parsing output")
            marker1 = "following untracked working tree files would be overwritten by merge"
            marker2 = "local changes to the following files would be overwritten by merge"
            for line in lines:
                logger.debug(repr(line))
                if marker1 in line or marker2 in line:
                    logger.info("Found interfering files!")
                    interfering_files = True
                    line = next(lines)
                    while line.startswith('\t'):
                        line = line.strip()
                        if not line.endswith('/'):
                            try:
                                dir, fname = os.path.split(line)
                                if not dir: dir = '.'
                                old_path, new_path = get_safe_file_backup_path(dir, fname)
                                logger.info("Moving interfering file {} to {}".format(line, new_path))
                                os.renames(old_path, new_path)
                                cls.moved_files.append((old_path, new_path))
                            except OSError:
                                logger.warning("Couldn't remove an interfering file {} while pulling!".format(line))
                        line = next(lines)
            if interfering_files:
                return cls.pull(source, branch, opts)
            else:
                raise e


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

    def update_on_firstboot(self, name="ZPUI update app firstboot dialog", suggest_restart=False):
        choice = DialogBox("yn", i, o, message="Update ZPUI?", name="ZPUI update app firstboot dialog").activate()
        if not choice:
            return None
        return self.update(suggest_restart=suggest_restart)

    def update(self, suggest_restart=True, skip_steps=None):
        logger.info("Starting update process")
        pb = ProgressBar(i, o, message="Updating ZPUI")
        pb.run_in_background()
        steps = self.get_steps()
        progress_per_step = 100 / len(steps)
        skip_steps = skip_steps if skip_steps else []

        completed_steps = []
        try:
            for step in steps:
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
    #safe_branches = ["master", "staging", "devel"] # commenting out for now because staging and devel are unused
    safe_branches = ["master"]
    # Forming the default config
    default_config = '{"url":"https://github.com/ZeroPhone/ZPUI", "branches":[], "check_revs":true, "run_tests":true, "auto_check_update":true, "check_update_on_open":true, "update_interval":3600, "ignored_updates":[]}'
    json_config = json.loads(default_config)
    json_config["branches"] = safe_branches
    default_config = json.dumps(json_config)

    def __init__(self):
        GenericUpdater.__init__(self)
        self.config = read_or_create_config(local_path(self.config_filename), self.default_config, "Git updater")
        self.save_config = save_config_method_gen(self, local_path(self.config_filename))
        self.check_revisions = self.config.get("check_revs", True)
        self.run_tests = self.config.get("run_tests", True)

    def get_steps(self):
        steps = ["check_connection", "check_git", "set_url", "check_revisions", "pull", "install_requirements", "pretest_migrations"]
        if self.config.get("run_tests", True):
            steps.append("tests")
        return steps

    def do_check_git(self):
        if not GitInterface.git_available():
            logger.exception("Couldn't execute git - not found?")
            raise OSError()

    def get_current_remote_revisions(self):
        GitInterface.command("fetch")
        current_branch_name = GitInterface.get_current_branch()
        current_revision = GitInterface.get_head_for_branch(current_branch_name)
        remote_revision = GitInterface.get_head_for_branch("origin/"+current_branch_name)
        logger.debug("Current: {}, remote: {}".format(current_revision, remote_revision))
        return current_revision, remote_revision

    def do_check_revisions(self):
        current_revision, remote_revision = self.get_current_remote_revisions()
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
        cmdline = ["pip", "install", "-r", "requirements.txt"]
        output = check_output(["pip", "--version"])
        if isinstance(output, bytes): output = output.decode("utf-8")
        pip, ver, other = output.split(' ', 2)
        #print(pip, ver)
        if packaging.version.parse(ver) > packaging.version.parse("23.0.0"):
            cmdline.insert(2, "--break-system-packages")
        output = check_output(cmdline)
        if isinstance(output, bytes): output = output.decode("utf-8")
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

    def toggle_check_revs(self):
        self.check_revisions = not self.check_revisions
        self.config["check_revs"] = self.check_revisions
        self.save_config()

    def toggle_auto_check_update(self):
        self.config["auto_check_update"] = not self.config["auto_check_update"]
        self.save_config()

    def toggle_check_update_on_open(self):
        self.config["check_update_on_open"] = not self.config["check_update_on_open"]
        self.save_config()

    def toggle_run_tests(self):
        self.run_tests = not self.run_tests
        self.config["run_tests"] = self.run_tests
        self.save_config()

    def human_readable_source(self, name):
        if name == "/" or name == '.':
            return "Core"
        if name == "test_commandline":
            return "Tests"
        elif name in logging_ui.logger_alias_map:
            # We have a defined name for this logger
            return logging_ui.logger_alias_map[name]
        elif name.startswith("ui."):
            # This is an UI element
            element_name = name[len("ui."):].capitalize()
            return "UI - {}".format(element_name.replace("_", " "))
        elif name.startswith("apps."):
            # This is an app
            if name.count('.') >= 2:
                app_name, module_name = name.rsplit(".", 2)[1:]
                if app_name.endswith("_apps"): app_name = app_name.rsplit('_', 1)[0]
                app_name = app_name.capitalize().replace("_", " ")
                return '{} app - {}'.format(app_name, module_name)
            elif name == "apps.zero_app":
                return 'ZeroApp'
            elif name == "apps.app_manager":
                return 'App manager'
            else:
                _, name = name.split('.', 1)
                return name.replace("_", " ").capitalize()
        elif name.startswith("input.drivers") or name.startswith("output.drivers"):
            if name.rstrip('/').endswith("drivers"):
                return name.replace("_", " ").capitalize()
            # This is a driver
            driver_name = name.rsplit(".", 1)[1].capitalize().replace("_", " ")
            driver_type = name.split(".", 1)[0]
            return '{} {} driver'.format(driver_name, driver_type)
        else: # couldn't interpret it
            return name.strip('.').replace("_", " ").capitalize()

    def updates_available(self):
        current_revision, remote_revision = self.get_current_remote_revisions()
        #return True # for testing
        return current_revision != remote_revision

    def list_updates(self):
        current_revision, remote_revision = self.get_current_remote_revisions()
        #current_revision = "56bfabefc908b041f9a0e" # for testing
        diff = GitInterface.get_diff(current_revision, remote_revision)
        if not diff: # empty diff - looks like there's no newer commits in the source! the discrepancy is likely explained by new local commits.
            return False
        #print(repr(diff))
        lines = []
        # this block is about making commit messages more human-readable; mostly, by reformatting the commit sources
        for line in diff.split('\n'):
            line = line.strip()
            commit, msg = line.split(' ', 1)
            if ":" in msg: # has a hopefully-properly formatted commit message
                source, changes = msg.split(':', 1)
                source = source.replace('/', '.').strip()
                try:
                    source = self.human_readable_source(source)
                except:
                    logger.exception("Failed to parse commit message {}!".format(repr(line)))
                    line = line
                else:
                    line = "{} {}:{}".format(commit, source, changes)
            else:
                line = "{} {}".format(commit, msg) # just leave it be
            lines.append(line)
        text = "\n".join(lines)
        #print(text)
        return text

    def update_is_interesting(self):
        _, remote_revision = self.get_current_remote_revisions()
        if remote_revision in self.config["ignored_updates"]:
            return False
        return True

    def show_updates(self):
        text = self.list_updates()
        if not text:
            return
        if not self.update_is_interesting():
            return False
        text += "\n"
        text += "\nPress Left to exit"
        TextReader(text, i, o, name="Settings app updates list TextReader").activate()
        self.update_on_firstboot(name="Settings app updates list update dialog", suggest_restart=True)
        choice = DialogBox("yn", i, o, message="Update ZPUI?", name="Settings app updates list update dialog").activate()
        if not choice:
            # mark update target as ignored for now
            PrettyPrinter("Marking update as uninteresting, then", i, o, 1)
            _, remote_revision = self.get_current_remote_revisions()
            self.config["ignored_updates"].append(remote_revision)
            self.save_config()
            return None
        return self.update(suggest_restart=True)

    def settings_contents(self):
        mc = [
            #["Select branch", self.pick_branch], # not that useful of an option right now
            ["Auto check for updates: {}".format("YES" if self.config["auto_check_update"] else "NO"), self.toggle_auto_check_update],
            ["Check updates on app open: {}".format("YES" if self.config["check_update_on_open"] else "NO"), self.toggle_check_update_on_open],
            ["Compare code: {}".format("YES" if self.check_revisions else "NO"), self.toggle_check_revs],
            ["Run tests: {}".format("YES" if self.run_tests else "NO"), self.toggle_run_tests],
            ["Change URL", self.change_origin_url]]
        return mc

    def settings(self):
        Menu([], i, o, contents_hook=self.settings_contents, name="Git updater settings menu").activate()

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
            if isinstance(output, bytes): output = output.decode("utf-8")
            logger.debug("pytest output:")
            logger.debug(output)
        except CalledProcessError as e:
            output = e.output
            if isinstance(output, bytes): output = output.decode("utf-8")
            logger.warning("pytest output:")
            logger.warning(output)
            raise

    def revert_pull(self):
        # do_check_revisions already ran, we now have the previous revision's
        # commit hash in self.previous_revision
        GitInterface.command("reset --hard {}".format(self.previous_revision))
        # if any files were moved, moving them back
        if GitInterface.moved_files:
            for old, new in GitInterface.moved_files:
                logger.info("Moving file back from {} to {}".format(new, old))
                os.renames(old, new)
            GitInterface.moved_files = []
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
                # making sure check_revisions is set to False
                old_check_revs = self.check_revisions
                self.check_revisions = False
                updated = self.update()
                self.check_revisions = old_check_revs
            except:
                PrettyPrinter("Couldn't check out the {} branch! Try resolving the conflict through the command-line.".format(branch), i, o, 3)
            else:
                PrettyPrinter("Now on {} branch!".format(branch), i, o, 2)
                self.suggest_restart()


class SettingsApp(ZeroApp):
    update_thread = None
    git_updater = None
    context = None
    update_zpui_fba = None
    updates_available = BooleanEvent()

    menu_name = "Settings"

    def updater(self):
        while self.git_updater.config.get('auto_check_update', False): # will immediately exit if auto_check_update is set to false
            self.check_updates()
            sleep(self.git_updater.config.get('update_interval', 3600)) # checks once an hour by default after the first check

    def check_updates(self):
        try:
            if self.git_updater.updates_available(): # git fetch and check happens here
                logger.debug("ZPUI updates available? Let's check the diff!")
                update_result = self.git_updater.list_updates()
                if update_result: # non-empty diff - means the remote actually has new commits for us
                    if self.git_updater.update_is_interesting():
                        logger.info("ZPUI updates available! {}".format(update_result))
                        self.updates_available.set(True)
                        self.status_updates_zone.request_refresh()
                        pass # uhhhh emit a notification? lol
                    else:
                        logger.info("ZPUI updates available, but marked as uninteresting")
                else:
                    logger.debug("ZPUI update correctly detected as non-applicable!")
        except:
            logger.exception("Problem when automatically fetching updates!")

    def status_updates_get(self):
        return bool(self.updates_available)

    def status_updates_icon(self, zone, value):
        if not value:
            return crop(zone.canvas.get_image()) # just empty image; we never use the canvas anyway
        icon = open_image(local_path("updates_icon.png"))
        icon = icon.convert(zone.o_params["device_mode"])
        if "color" in zone.o_params['type']:
            icon = replace_color(icon, "white", zone.canvas.default_color)
        return icon

    def set_context(self, c):
        self.context = c
        self.context.register_firstboot_action(bugreport_ui.autosend_optin_fba)
        self.context.register_firstboot_action(self.update_zpui_fba)
        self.status_updates_zone = Zone(self.status_updates_get, self.status_updates_icon, name="ZPUI updates")
        self.context.set_provider("statusbar_updates", self.status_updates_zone)

    def init_app(self):
        # globals for the remainder of the UI to use, until it's refactored
        global i, o
        i = self.i
        o = self.o
        # globals for other modules
        logging_ui.i = self.i
        logging_ui.o = self.o
        bugreport_ui.i = self.i
        bugreport_ui.o = self.o
        bugreport_ui.git_if = GitInterface
        about.i = self.i
        about.o = self.o
        about.git_if = GitInterface
        self.git_updater = GitUpdater()
        self.update_zpui_fba = FirstBootAction("update_zpui", self.git_updater.update_on_firstboot, depends=["check_connectivity"])
        self.update_thread = BackgroundRunner(self.updater)
        self.check_on_open_br = BackgroundRunner(self.check_updates)
        if self.git_updater.config.get('auto_check_update', False):
            self.update_thread.run()

    def on_start(self):
        if self.git_updater.config.get('check_update_on_open', False):
            # launch a background thread checking for updates
            self.check_on_open_br.run()
        def contents_hook():
            c = [["Update ZPUI", self.git_updater.update, self.git_updater.settings],
                 # ["Bugreport", bugreport_ui.main_menu], # no longer working, big sad
                 ["Logging settings", logging_ui.config_logging],
                 ["About", about.about]]
            if self.updates_available:
                l = ["Updates available!", self.git_updater.show_updates]
                c = [l] + c
            return c
        menu = Menu([], self.i, self.o, contents_hook=contents_hook, name="ZPUI settings menu")
        #help_text = "Press RIGHT on \"Update ZPUI\" to change OTA update settings (branch or git URL to use)"
        #HelpOverlay(help_text).apply_to(menu)
        menu.activate()
