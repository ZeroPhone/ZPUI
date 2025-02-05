import os
import json
from copy import copy
from collections import OrderedDict

from apps import ZeroApp
from actions import FirstBootAction as FBA
from helpers import is_emulator, setup_logger, flatten, local_path_gen, cb_needs_key_state, KEY_HELD
from ui import DialogBox, Canvas, HelpOverlay, Refresher, GraphicsPrinter, RefresherExitException, PrettyPrinter as Printer, GraphicsPrinter

from __main__ import cm

logger = setup_logger(__name__, "info")

firstboot_filename = "zpui_firstboot.list"

firstboot_file_locations = [firstboot_filename, "/tmp/"+firstboot_filename]
if not is_emulator():
    firstboot_file_locations = ["/boot/"+firstboot_filename]+firstboot_file_locations

local_path = local_path_gen(__name__)

# This ordering is applied after the dependencies are sorted out,
# in a way that should not disturb the dependency-related ordering changes.
# Nevertheless, it'd be cool if it could be covered with tests of some kind,
# to make sure the ordering is both applied well and doesn't break the dependency chain.

firstboot_action_ordering = \
[
  'apps.firstboot_wizard%learn_about_5_buttons',
  'apps.firstboot_wizard%learn_about_zeromenu',
  'apps.firstboot_wizard%learn_about_help_icon',
  'apps.system_apps.users_groups%change_password',
  'apps.network_apps.ssh%ssh_setup',
  'apps.network_apps.wifi_settings%change_wifi_country',
  'apps.personal.clock%set_timezone',
  'apps.network_apps.wpa_cli%connect_to_wifi', # this and check_conn could use some kind of soft "dependency" for ordering - i.e. "after"?
  'apps.network_apps.internet_tools%check_connectivity',
  'apps.personal.clock%force_sync_time',
  'apps.settings%error_log_auto_send',
  'apps.system_apps.shutdown%reboot_after_firstboot'
]

class FirstbootWizard(ZeroApp):
    def learn_about_5_buttons(self):
        c = Canvas(self.o)
        c.centered_text("Let's go through\nthe main buttons\nand their meanings")
        GraphicsPrinter(c.get_image(), self.i, self.o, 5, invert=False)
        c.clear()
        c.centered_text("Press the buttons\nto test\nThen ENTER\nto continue")
        GraphicsPrinter(c.get_image(), self.i, self.o, 5, invert=False)
        c.clear()
        # First, show the left/right/up/down buttons
        # TODO: different behaviour for ZP and emulator?
        c.text("Enter", (48, 22))
        c.text("Continue", (39, 30))
        c.text("Left", (2, 18))
        c.text("Back", (2, 26))
        c.text("Cancel", (2, 34))
        c.text("Right", (92, 22))
        c.text("Option", (90, 30))
        c.text("Up", (56, 5))
        c.text("Down", (52, "-18"))
        image = c.get_image()
        def process_key(key, state):
            # invert/deinvert areas on the canvas when buttons are pressed/released
            # on drivers that don't support key states, will toggle inversion on every press
            # on drivers that support key states, will "highlight" the buttons pressed
            print(key, state)
            if state != KEY_HELD:
                if key == "KEY_UP":
                    c.invert_rect((64-20, 2, 64+20, 22))
                elif key == "KEY_DOWN":
                    c.invert_rect((64-20, "-2", 64+20, "-22"))
                elif key == "KEY_LEFT":
                    c.invert_rect((2, 32-15, 38, 32+15))
                elif key == "KEY_RIGHT":
                    c.invert_rect(("-2", 32-10, "-40", 32+10))
        keys = ["KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT"]
        keymap = {"KEY_ENTER":"deactivate"}
        for key in keys:
            cb = cb_needs_key_state(lambda st, x=key: process_key(x, st))
            keymap[key] = cb
        Refresher(c.get_image, self.i, self.o, override_left=False, keymap=keymap).activate()
        return True

    def learn_about_help_icon(self):
        o = HelpOverlay("test")
        c = Canvas(self.o)
        c.text("See this icon?->", (1, 1))
        c.text("When it appears,", (3, 10))
        c.text("press F5 to get help", (3, 19))
        c.text("Try now, or", (3, 28))
        c.text("press ENTER to skip", (3, 37))
        if not is_emulator():
            c.text("F5:", (5, 51))
            c.paste(local_path("f5_button_location.png"), (30, 50), invert=True)
        o.draw_icon(c)
        Refresher(c.get_image, self.i, self.o, keymap={"KEY_ENTER":"deactivate", "KEY_F5":self.on_help_button_press}).activate()
        return True

    def learn_about_zeromenu(self):
        c = Canvas(self.o)
        if is_emulator():
            c.text("Press F11 to get", (1, 1))
        else:
            c.text("Press PROG2 to get", (1, 1))
        c.text("a shortcut menu -", (3, 10))
        c.text("ZeroMenu. You can", (3, 19))
        c.text("add apps to it", (3, 28))
        c.text("for quick launch", (3, 37))
        if not is_emulator():
            c.text("PROG2:", (5, 51))
            c.paste(local_path("prog2_button_location.png"), (40, 50), invert=True)
        Refresher(c.get_image, self.i, self.o, keymap={"KEY_ENTER":"deactivate", "KEY_PROG2":self.on_zeromenu_button_press}).activate()
        return True

    def on_help_button_press(self):
        c = Canvas(self.o)
        c.centered_text("Good job!\nThe button\nseems to work\n;-P")
        GraphicsPrinter(c.get_image(), self.i, self.o, 3, invert=False)
        raise RefresherExitException

    def on_zeromenu_button_press(self):
        c = Canvas(self.o)
        c.centered_text("Good job!\nZeroMenu button\nseems to work!")
        GraphicsPrinter(c.get_image(), self.i, self.o, 3, invert=False)
        raise RefresherExitException

    def set_context(self, c):
        self.context = c
        #self.context.set_target(self.do_firstboot)
        self.context.threaded = False
        self.context.register_firstboot_action(FBA("learn_about_5_buttons", self.learn_about_5_buttons))
        self.context.register_firstboot_action(FBA("learn_about_help_icon", self.learn_about_help_icon))
        self.context.register_firstboot_action(FBA("learn_about_zeromenu", self.learn_about_zeromenu))

    def execute_after_contexts(self):
        self.do_firstboot()

    def sort_actions_by_ordering(self, actions, actions_involved_in_dependencies):
        # needs tests lol
        # Actions passed here are already sorted by dependencies
        def get_preceding_action(action_fullname):
            if action_fullname not in firstboot_action_ordering:
                return False
            if firstboot_action_ordering.index(action_fullname) == 0:
                return None
            index = firstboot_action_ordering.index(action_fullname)
            return firstboot_action_ordering[index-1]
        # here, we'll deconstruct the original OrderedDict, sort the items
        # and then build a new OrderedDict out of these
        tail = []
        sorted_part = []
        pass_counter = 0
        while True:
            # O(n)
            # I mean, I sure hope so
            already_sorted_action_names = [a[0] for a in sorted_part+tail]
            if set(already_sorted_action_names) == set(actions.keys()):
                break
            logger.info("Firstboot action ordering sort pass {}".format(pass_counter))
            pass_counter += 1
            if pass_counter > len(actions.keys()):
                logger.error("Can't finish sorting in a reasonable amount of time! 0_0")
                break
            for action_fullname, action in actions.items():
                if action_fullname in already_sorted_action_names:
                    continue
                preceding_action = get_preceding_action(action_fullname)
                if preceding_action is False:
                    # Not even in the ordering, just add it in the end
                    tail.append((action_fullname, action))
                elif action_fullname in actions_involved_in_dependencies:
                    # Action involved in a dependency, that overrides ordering - just add it as-is
                    sorted_part.append((action_fullname, action))
                elif preceding_action is None:
                    # First element and not involved in a dependency
                    sorted_part.insert(0, (action_fullname, action))
                else:
                    # there is a preceding action in the ordering!
                    if preceding_action in [i[0] for i in sorted_part]:
                        index = [i[0] for i in sorted_part].index(preceding_action)
                        sorted_part.insert(index+1, (action_fullname, action))
                    elif preceding_action in [i[0] for i in tail]:
                        # WTF WTF
                        logger.error("Excuse me, what? {} {} {}".format(action_fullname, preceding_action, sorted_part, tail, actions.keys()))
                    elif preceding_action not in actions.keys():
                        # if the preceding action is not even present, just adding
                        sorted_part.append((action_fullname, action))
                    else:
                        pass # preceding action is not in the list yet, doing nothing
        # in the end, we make a list of key,value pairs to pass to the OrderedDict constructor
        dict_items = sorted_part+tail
        return OrderedDict(dict_items)

    def get_firstboot_file(self):
        """ Returns ``(filename, is_new_file)``, ``(None, False)`` on failure """
        file = None
        for file in firstboot_file_locations:
            if os.path.exists(file):
                logger.info("Firstboot list file {} found".format(file))
                return (file, False)
        else:
            logger.info("No firstboot list files found, creating one")
            for file_path in firstboot_file_locations:
                # try and touch the file
                try:
                    open(file_path, "w").close()
                except:
                    logger.exception("Can't create a firstboot list file at {}, skipping".format(file_path))
                else:
                    logger.info("Created a firstboot list file at {}".format(file_path))
                    return (file, True)
            else:
                # We can't create any files!
                logger.error("Can't create any of the firstboot list files! Locations: {}".format(firstboot_file_locations))
                return (None, False)

    def get_completed_actions_from_file(self, file):
        actions = []
        try:
            with open(file, 'r') as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
                for line in lines:
                  try:
                    action_dict = json.loads(line)
                  except ValueError:
                    actions.append(line)
                  else:
                    actions.append(action_dict)
            return actions
        except:
            logger.exception("Couldn't load completed actions from firstboot list file")
            return []

    def do_firstboot(self):
        firstboot_actions = cm.am.get_firstboot_actions()
        # Skipping actions that shouldn't be run in an emulator
        if is_emulator():
            firstboot_action_names = [name for name, action in firstboot_actions.items() if not action.not_on_emulator]
        else:
            firstboot_action_names = list(firstboot_actions.keys())
        firstboot_file, is_new_file = self.get_firstboot_file()
        if firstboot_file is None:
            logger.error("Can't read/create a firstboot file, no sense for the firstboot application to continue")
            return
        completed_action_names = []
        failed_action_names = []
        skipped_action_names = []
        if not is_new_file:
            completed_action_names = []
            completed_actions = self.get_completed_actions_from_file(firstboot_file)
            for action in completed_actions:
                if isinstance(action, basestring):
                    completed_action_names.append(action)
                elif isinstance(action, dict):
                    action_name = action["action"]
                    action_result = action["status"]
                    if action_result == "success":
                        # If action has been recorded as failed/skipped before and later was marked as successful
                        # we don't need to count the fails/skips in
                        while action_name in skipped_action_names: skipped_action_names.remove(action_name)
                        while action_name in failed_action_names: failed_action_names.remove(action_name)
                        completed_action_names.append(action_name)
                    elif action_result == "fail":
                        # if action failed before, it being skipped before/after is irrelevant
                        failed_action_names.append(action_name)
                        while action_name in skipped_action_names: skipped_action_names.remove(action_name)
                    elif action_result == "skip":
                        if action_name not in failed_action_names:
                            skipped_action_names.append(action_name)
        non_completed_action_names = [n for n in firstboot_action_names if n not in completed_action_names and n not in skipped_action_names]
        # print(non_completed_action_names, skipped_action_names, failed_action_names, completed_action_names)
        if non_completed_action_names:
            if is_new_file or (not completed_action_names and not skipped_action_names and not failed_action_names):
                # first boot, no info whatsoever yet
                message = "Let's go through first boot setup!"
            elif not completed_action_names and not failed_action_names: # Not the first boot - some actions have been completed before
                message = "New setup actions for your ZP found!"
            elif failed_action_names and set(completed_action_names) == set(failed_action_names): # Some actions have not been successfully completed
                message = "Want to retry failed first boot actions?"
            else: # ought to make a truth table, I guess
                message = "New setup actions for your ZP found!"
            if not self.context.request_exclusive():
                logger.error("Can't get an exclusive context switch, exiting")
                return
            choice = DialogBox('yn', self.i, self.o, message=message, name="Firstboot wizard setup menu").activate()
            if not choice:
                self.context.rescind_exclusive()
                return
            else:
                # User confirmed that they want to go through with the firstboot wizard
                # Let's sort the actions and resolve their dependencies
                # For that, we need some storage variables.
                # Here, we store actions by their fullname, sorted in order to
                # resolve the dependency problems
                sorted_actions = OrderedDict()
                # Here, we store lists of actions that depend on some other action,
                # sorted by the execution order (after resolving the dependencies)
                action_dependants = {}
                # Here, we store action fullnames (provider+separator+name)
                # by their short names (just action name, no 'provider' appended)
                # because short names are used in dependencies.
                action_fullname_by_name = {}
                def get_prov_and_name(action_fullname):
                    return action_fullname.split(cm.am.action_name_delimiter, 1)
                # First, creating a lookup table for looking up dependencies
                for action_fullname in firstboot_action_names:
                    _, action_name = get_prov_and_name(action_fullname)
                    action_fullname_by_name[action_name] = action_fullname
                # Then, compiling the list of actions that depend on other action
                for action_fullname in non_completed_action_names:
                    _, action_name = get_prov_and_name(action_fullname)
                    action = firstboot_actions[action_fullname]
                    if action.depends:
                        has_unresolved_dependencies = False
                        for dependency in action.depends:
                            dep_fullname = action_fullname_by_name.get(dependency, None)
                            if dep_fullname is None:
                                logger.error("Dependency {} for action {} is not found!".format(dep_fullname, action_name))
                                continue
                            if dep_fullname in non_completed_action_names:
                                has_unresolved_dependencies = True
                                # dependency hasn't been completed yet
                                if dep_fullname in action_dependants:
                                    action_dependants[dep_fullname].append(action_fullname)
                                else:
                                    action_dependants[dep_fullname] = [action_fullname]
                            else:
                                logger.info("Dependency {} (for action {}) is already completed!".format(dep_fullname, action_name))
                        if not has_unresolved_dependencies:
                            # No non-completed dependencies have been found
                            # so, we can just add the action to the list
                            sorted_actions[action_fullname] = action
                    else:
                        # Action doesn't depend on anything, just adding it to the list
                        sorted_actions[action_fullname] = action
                # This code untangles an arbitrarily long chain of dependencies
                # except, well, circular dependencies
                actions_involved_in_dependencies = []
                if action_dependants:
                    original_dependants = copy(action_dependants)
                    logger.info("Resolving dependencies: {}".format(action_dependants))
                    while action_dependants:
                        all_dependency_actions = action_dependants.keys()
                        all_dependent_actions = flatten(action_dependants.values())
                        independent_dependencies = [n for n in all_dependency_actions if n not in all_dependent_actions]
                        if not independent_dependencies:
                            logger.error("No independent dependencies found while resolving dependencies: {} (original: {})!".format(action_dependants, original_dependants))
                            return
                        for action_fullname in independent_dependencies:
                            if action_fullname not in sorted_actions:
                                sorted_actions[action_fullname] = firstboot_actions[action_fullname]
                                actions_involved_in_dependencies.append(action_fullname)
                            action_dependants.pop(action_fullname)
                    # The while() has run its course and the dependencies have been linearized
                    all_dependent_actions = flatten(original_dependants.values())
                    all_unadded_dependent_actions = [n for n in all_dependent_actions \
                      if n not in sorted_actions]
                    for action_fullname in all_unadded_dependent_actions:
                        sorted_actions[action_fullname] = firstboot_actions[action_fullname]
                        actions_involved_in_dependencies.append(action_fullname)
                    logger.info("Dependencies resolved!")
                # Sorting actions for consistent firstboot experience
                sorted_actions = self.sort_actions_by_ordering(sorted_actions, actions_involved_in_dependencies)
                # Now, executing actions one-by-one
                failed_actions = []
                log_completed_action_has_failed = False
                for action_fullname, action in sorted_actions.items():
                    if action.depends:
                        if any([d in failed_actions for d in action.depends]):
                            logger.error("Not executing action {} because some of its dependencies ({}) are among failed dependencies: {}".format(action_fullname, action.depends, failed_actions))
                            continue
                    action_provider, action_name = get_prov_and_name(action_fullname)
                    if action.will_context_switch:
                        self.context.request_switch(action_provider, start_thread=False)
                    try:
                        result = action.func()
                    except:
                        logger.exception("Action {} failed to execute!".format(action_fullname))
                        failed_actions.append(action_name)
                    else:
                        if result is False: # Action failed internally
                            failed_actions.append(action_name)
                        status = {False:"fail", True:"success", None:"skip"}.get(result, "success")
                        action_dict = {"action":action_fullname, "status":status}
                        action_result = json.dumps(action_dict)
                        try:
                            with open(firstboot_file, 'a') as f:
                                f.write(action_result+'\n')
                        except:
                            # Avoid cluttering the logs - logger.exception writes the entire traceback into logs
                            # while logger.error just writes the error message
                            if not log_completed_action_has_failed:
                                logger.exception("Can't write action {} into firstboot logfile {}!".format(action_fullname, firstboot_file))
                                log_completed_action_has_failed = True
                            else:
                                logger.error("Can't write action {} into firstboot logfile {}!".format(action_fullname, firstboot_file))
                    self.context.request_switch()
