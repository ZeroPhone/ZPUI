import os
from copy import copy

from apps import ZeroApp
from ui import Menu, Refresher, Checkbox, Listbox, DialogBox, RefresherExitException, ProgressBar, LoadingIndicator, PrettyPrinter, Printer, Canvas, UniversalInput, PathPicker, GraphicsPrinter, IntegerAdjustInput
from helpers import ExitHelper, read_or_create_config, local_path_gen, save_config_method_gen, read_config
local_path = local_path_gen(__name__)

from subprocess import call

from libs.pyavrdude import pyavrdude, heuristics

import graphics

class AvrdudeApp(ZeroApp):
    menu_name = "Avrdude"
    default_config = '{"default_part":"m328p", "default_programmer":"usbasp", "last_write_file":"/tmp/tmp.hex", "last_read_filename":"tmp", "last_read_dir":"/tmp", "last_write_fuse_params":[], "filter_programmers":true, "last_bitclock":5, "bootloader_config_filename":"bootloaders.json"}'
    config_filename = "config.json"

    # These programmers are selected on whether they:
    # 1. don't require a bootloader (otherwise pyavrdude.detect_chip breaks)
    #   So, "arduino" and similar are out
    #   Especially since "arduino" requires to use a serial port
    #   and we don't yet have a way to set it
    # 2. make sense on ZeroPhone (LPT and COM programmers are out)
    supported_programmers = ["usbasp", "avrisp2", "usbasp-clone", "usbtiny", "pickit2"]
    # These are the fuse types that will, by default, be offered for read/
    # autodetected for write
    fuse_types = ["hfuse", "lfuse", "efuse"]
    flash_format = 'i'
    fuse_format = 'i'

    def __init__(self, *args, **kwargs):
        ZeroApp.__init__(self, *args, **kwargs)
        # Initializing variables from config file
        self.config = read_or_create_config(local_path(self.config_filename), self.default_config, self.menu_name+" app")
        self.save_config = save_config_method_gen(self, local_path(self.config_filename))
        self.current_chip = self.config["default_part"]
        self.current_programmer = self.config["default_programmer"]
        self.filter_programmers = self.config["filter_programmers"]
        self.bitclock = self.config["last_bitclock"]
        self.read_filename = self.config["last_read_filename"]
        self.read_dir = self.config["last_read_dir"]
        self.write_file = self.config["last_write_file"]
        self.write_fuse_params = self.config["last_write_fuse_params"]
        self.bootloader_config_filename = self.config["bootloader_config_filename"]
        # Creating UI elements to be used in run_and_monitor_process()
        # they're reusable anyway, and we don't have to init them each time
        # that we enter run_and_monitor_process() .
        self.erase_restore_indicator = LoadingIndicator(self.i, self.o, message = "Erasing")
        self.read_write_bar = ProgressBar(self.i, self.o)

    def set_context(self, context):
        """
        A ZPUI-specific function to get the context. For now, is used to avoid
        polling the chip if the app not the one active.
        """
        self.context = context

    # Avrdude application flow:
    # 1. Main menu - select action (read/write/erase)
    # 2. Parameters are set up and checked
    # 3. A process is created
    # 4. Files/options are added to the process' commandline
    # 5. Chip is detected
    # 6. Process is started and monitored

    # 1. Main menu

    def check_avrdude_available(self):
       try:
           with open(os.devnull, "w") as f:
              assert( call(['avrdude'], stdout=f, stderr=f) == 0 )
           return True
       except (AssertionError, OSError):
           return False

    def on_start(self):
        if not self.check_avrdude_available():
            PrettyPrinter("Avrdude not available!", self.i, self.o, 3)
            return
        mc = [["Read chip", self.read_menu],
              ["Write chip", self.write_menu],
              ["Erase chip", self.erase_menu],
              ["Pick programmer", self.pick_programmer],
              ["Pick chip", self.pick_chip],
              ["Pinouts", lambda: graphics.show_pinouts(self.i, self.o)],
              ["Settings", self.settings_menu]]
        Menu(mc, self.i, self.o, name="Avrdude app main menu").activate()

    # 2. Initial read/write/erase menus and safety checks

    def read_menu(self):
        def verify_and_run():
            """
            If either directory that we need to read into does not exist,
            the filename is invalid or there is already an invalid file in that
            location (character device or something like that), we should warn
            the user and abort.
            If there's already a file in that location, we should make the
            user confirm the overwrite.
            """
            full_path = os.path.join(self.read_dir, self.read_filename)+".hex"
            if not os.path.isdir(self.read_dir):
                PrettyPrinter("Wrong directory!", self.i, self.o, 3)
                return
            if '/' in self.read_filename:
                PrettyPrinter("Filename can't contain a slash!", self.i, self.o, 3)
                return
            if os.path.exists(full_path):
                if os.path.isdir(full_path) or not os.path.isfile(full_path):
                    PrettyPrinter("Trying to overwrite something that is not a file!", self.i, self.o, 5)
                    return
                choice = DialogBox('ync', self.i, self.o, message="Overwrite?", name="Avrdude write overwrite confirmation").activate()
                if not choice:
                    return
            self.create_process()
            if self.read_checklist():
                self.detect_and_run()
        # Needs to be autogenerated so that filename/path update after changing them
        def get_contents():
            contents = [["Filename: {}".format(self.read_filename), lambda: self.set_filename("read_filename", "last_read_filename", message="Read filename:")],
                        ["Folder: {}".format(self.read_dir), lambda: self.set_dir("read_dir", "last_read_dir")],
                        ["Continue", verify_and_run]]
            return contents
        Menu([], self.i, self.o, contents_hook=get_contents, name="Avrdude read parameter menu", append_exit=False).activate()

    def write_menu(self):
        def verify_and_run():
            """
            If file that we need to write to the chip does not exist, we should
            warn the user and abort.
            """
            if not (os.path.exists(self.write_file) and os.path.isfile(self.write_file)):
                PrettyPrinter("File does not exist/invalid!", self.i, self.o, 2)
                return
            self.create_process()
            if self.write_checklist():
                self.detect_and_run()
        # Needs to be autogenerated so that filename updates after changing them
        def get_contents():
            if self.write_file:
                dir, filename = os.path.split(self.write_file)
            else:
                dir, filename = '/', 'None'
            contents = [["File: {}".format(filename), lambda x=dir: self.set_write_file(x)],
                        ["Use bootloader", self.pick_bootloader],
                        ["Use last read file", self.set_write_as_last_read],
                        ["Continue", verify_and_run]]
            return contents
        Menu([], self.i, self.o, contents_hook=get_contents, name="Avrdude write parameter menu", append_exit=False).activate()

    def erase_menu(self):
        """
        This function is only named this way for naming consistency.
        There's no menu - at least, not yet; it simply checks whether
        the user presses "Yes" in a DialogBox.
        """
        self.create_process()
        if self.erase_checklist():
            self.detect_and_run()

    # 3. Process creation

    def create_process(self):
        """Creates the avrdude process."""
        self.p = pyavrdude.AvrdudeProcess(self.current_chip, self.current_programmer, parameters=self.get_avrdude_parameters())

    def get_avrdude_parameters(self):
        """
        Returns the additional parameters for avrdude to use.
        For now, only works with bitclock; other parameters (including
        programmer-specific ones) can be added here later.
        Is used both by ``detect_chip()`` and ``create_process()``.
        """
        return ['-B', str(self.bitclock)]

    # 4. Read/write/erase setup functions concerning file types and fuses

    def read_checklist(self):
        """
        Asks about types of memory that you'd like to read -
        for now, hardcoded to ["flash", "hfuse", "lfuse", "efuse"].
        Doesn't yet check if the MCU actually has the type of memory requested.

        This version only supports reading fuses using the 'i' mode - for now.
        """
        types = ["flash"] + self.fuse_types
        choices = [[c.capitalize(), c] for c in types]
        choices = Checkbox(choices, self.i, self.o, default_state=True, name="Avrdude read memory selection checkbox").activate()
        base_filename = self.read_filename
        if not choices:
            return False
        for choice in choices:
            if choices[choice]: # Flash is read by default
                extension = "hex" if choice == "flash" else choice
                format = self.flash_format if choice == "flash" else self.fuse_format
                file_path = os.path.join(self.read_dir, "{}.{}".format(base_filename, extension))
                self.p.setup_read(file_path, memtype=choice, format=format)
        return True

    def write_checklist(self):
        """
        Asks about types of memory that you'd like to write. When writing a bootloader,
        it adds the fuses to avrdude CLI parameters as text. When writing a .hex file or
        a backup created by read_checklist(), checks if there are additional fuse files
        present and adds them to avrdude CLI parameters.
        """
        if self.write_fuse_params:
            # Text fuse parameters detected, formatting them properly
            memory_params = [["flash", self.write_file, self.flash_format]]
            memory_params += copy(self.write_fuse_params)
        else:
            # No text fuse parameters found, looking for files
            memory_params = self.autodetect_memory_files(self.write_file)
        if memory_params:
            # If there are additional fuse files/settings present,
            # we give the user a chance to opt-out
            choices = [[type.capitalize(), type] for type, _, _ in memory_params]
            # Adding the "Flash" choice in front, as we certainly have that
            # but the user might want to only flash fuses
            #choices = [["Flash", "flash"]] + choices
            choices = Checkbox(choices, self.i, self.o, default_state=True, name="Avrdude write memory selection checkbox").activate()
            if not choices: # user exited the listbox
                return False # they likely don't want to continue
            for type, value, format in memory_params:
                if choices.get(type, False): # type selected
                    self.p.setup_write(value, memtype=type, format=format)
        else: # No fuse files/settings found
            # Add the flash file and proceed without a checkbox, no fuses
            self.p.setup_write(self.write_file, memtype="flash", format=self.flash_format)
        return True

    def erase_checklist(self):
        """
        Asks user if they really want to erase the chip.
        """
        answer = DialogBox('yn', self.i, self.o, message = "Are you sure?", name="Avrdude app erase verify dialogbox").activate()
        if answer:
            self.p.setup_erase()
        return answer

    # 5. "Chip detection" screen functions
    ## Status image functions

    def detect_and_run(self):
        """
        Runs the chip detection loop which stops once the chip is detected
        (or user exits). If a chip is detected, proceeds to launch the avrdude
        process.
        """
        Printer("Detecting...", self.i, self.o, 0)
        self.detect_loop()
        # Refresher has exited by now - either because of RefresherExitException
        # or because the user pressed LEFT
        # if a chip is found, it's likely the former
        status = self.get_status()
        if not heuristics.chip_is_found(status):
            return # Likely a LEFT press
        hrs = heuristics.get_human_readable_status(status)
        self.display_status(hrs)
        self.run_and_monitor_process()

    def detect_loop(self):
        """
        The detect loop. Will exit on RefresherExitException (raised by
        ``show_chip_status`` or on KEY_LEFT from the user.
        """
        r = Refresher(self.get_current_status_data, self.i, self.o, name="Avrdude chip detect loop")
        r.activate()

    def get_current_status_data(self):
        """
        A callback for the status Refresher. In future, if compatibility with
        text-based screens is needed, can fall back to ``show_chip_status()``-provided
        data.
        """
        status = self.show_chip_status()
        return graphics.make_image_from_status(self.o, status, success_message="Found chip!")

    def display_status(self, hrs, success_message = "Found chip!", delay=1):
        """
        Simply shows the provided status on the screen using a GraphicsPrinter.
        """
        image = graphics.make_image_from_status(self.o, hrs, success_message=success_message)
        GraphicsPrinter(image, self.i, self.o, delay, invert=False)

    ## Status text functions

    def show_chip_status(self):
        """
        A callback for the Refresher to get human-readable status data.
        Raises the RefresherExitException once a chip is found; is
        context-aware and will not poll status (thereby polling the
        hardware) when the app is not the one active.
        """
        if self.context.is_active():
            status = self.get_status()
            readable_status = heuristics.get_human_readable_status(status)
            if heuristics.chip_is_found(status):
                raise RefresherExitException
            return readable_status
        else:
            return ["Not probing", "App inactive"]

    def get_status(self):
        """
        Simply gets the status (non-human-readable) from the pyavrdude library.
        """
        return pyavrdude.detect_chip(self.current_chip, self.current_programmer, *self.get_avrdude_parameters())

    # 6. Avrdude process monitor state machine

    def run_and_monitor_process(self):
        """
        Starts and monitors the avrdude process; updating the user
        on its status. Activates/deactivates and updates loading indicators,
        then shows a status image once process is completed. In the future,
        will also allow sending bugreports about yet-unknown failures during
        the process.
        """
        self.p.run()
        previous_s = {"status": "not received yet"}
        while previous_s['status'] not in ["success", "failure"]:
            self.p.poll()
            s = self.p.get_interactive_status()
            if s != previous_s:
                # Status changed, updating
                if s["status"] == "started":
                    self.read_write_bar.pause()
                    self.erase_restore_indicator.background_if_inactive()
                    self.erase_restore_indicator.message = "Started"
                elif s["status"] == "in progress":
                    if s["operation"] in ["reading", "writing", "verifying"]:
                        self.erase_restore_indicator.pause()
                        self.read_write_bar.background_if_inactive()
                        self.read_write_bar.message = s["operation"].capitalize()
                        self.read_write_bar.message += " " + s["time"]
                        self.read_write_bar.progress = s["progress"]
                    elif s["operation"] in ["erasing", "restoring fuses"]:
                        self.read_write_bar.pause()
                        self.erase_restore_indicator.message = s["operation"].capitalize()
                elif s["status"] in ["success", "failure"]:
                    pass # Is going to fail/succeed anyway once it goes through all the lines
                previous_s = s
        # Process is over, showing the result
        self.read_write_bar.stop()
        self.erase_restore_indicator.stop()
        status = self.p.get_status()
        hrs = heuristics.get_human_readable_status(status)
        self.display_status(hrs, success_message = "Done!", delay=1)
        #if hrs == ['Failure', 'Unknown error']:
        #    # Unknown error
        #    # Once bugreport library is ready, we can offer the user to send a bugreport

    # PathPickers and Inputs for editing read/write paths - also save config variables

    def set_write_file(self, dir):
        """
        A function to set the writing file specifically. Calls ``self.set_file``,
        then resets the ``write_fuse_params`` if a file was chosen.
        """
        if self.set_file(dir, "write_file", "last_write_file"):
            # A file was picked manually, resetting fuse write params
            self.write_fuse_params = []
            self.config["last_write_fuse_params"] = self.write_fuse_params
            self.save_config()

    def set_file(self, dir, attr_name, config_option_name):
        """
        A function for selecting files (specifically, a full path to an existing
        file. For now, is only used for "write_file".
        """
        original_file = getattr(self, attr_name)
        dir, filename = os.path.split(original_file)
        # The original dir might not exist anymore, we might need to go through directories
        # until we find a working one
        while dir and not (os.path.exists(dir) and os.path.isdir(dir)):
            dir = os.path.split(dir)[0]
        if not dir:
            dir = '/'
        file = PathPicker(dir, self.i, self.o, file=filename).activate()
        if file and os.path.isfile(file):
            setattr(self, attr_name, file)
            self.config[config_option_name] = file
            self.save_config()
            return True

    def set_dir(self, attr_name, config_option_name):
        """
        A convenience wrapper for setting directories. For now, is only
        used for "read_dir".
        """
        original_dir = getattr(self, attr_name)
        dir = original_dir if original_dir else "/"
        dir = PathPicker(dir, self.i, self.o, dirs_only=True).activate()
        if dir:
            setattr(self, attr_name, dir)
            self.config[config_option_name] = dir
            self.save_config()
            return True

    def set_filename(self, attr_name, config_option_name, message="Filename:"):
        """
        A convenience wrapper for setting filenames. For now, is only used for
        "read_filename".
        """
        original_value = getattr(self, attr_name)
        value = original_value if original_value else ""
        filename = UniversalInput(self.i, self.o, message=message, value=value).activate()
        if filename:
            setattr(self, attr_name, filename)
            self.config[config_option_name] = filename
            self.save_config()
            return True

    # Various settings

    def pick_bootloader(self):
        """
        A menu to pick the bootloader from bootloaders.json.
        Also records fuse information in self.write_fuse_params,
        where it stays until user selects another bootloader
        or manually selects a file by path.
        """
        bootloader_dir = local_path("bootloaders/")
        config = read_config(os.path.join(bootloader_dir, self.bootloader_config_filename))
        bootloader_choices = [[bootloader["name"], bootloader] for bootloader in config["bootloaders"]]
        if not bootloader_choices:
            PrettyPrinter("No bootloaders found!", self.i, self.o, 3)
            return
        choice = Listbox(bootloader_choices, self.i, self.o, name="Avrdude bootloader picker").activate()
        if choice:
            self.write_file = os.path.join(bootloader_dir, choice["file"])
            self.write_fuse_params = []
            for type in self.fuse_types:
                if type in choice:
                    self.write_fuse_params.append([type, choice[type], config["fuse_format"]])
            self.config["last_write_file"] = self.write_file
            self.config["last_write_fuse_params"] = self.write_fuse_params
            self.save_config()

    def pick_chip(self):
        """ A menu to pick the chip from a list of available chips provided by
        avrdude. """
        chips = pyavrdude.get_parts()
        lc = [[name, alias] for alias, name in chips.items()]
        choice = Listbox(lc, self.i, self.o, "Avrdude part picker listbox", selected=self.current_chip).activate()
        if choice:
            self.current_chip = choice
            self.config["default_part"] = self.current_chip
            self.save_config()

    def pick_programmer(self):
        """ A menu to pick the programmer from a list of available programmers
        provided by avrdude. """
        programmers = pyavrdude.get_programmers()
        if self.filter_programmers:
            programmers = self.get_filtered_programmers(programmers)
        lc = [[name, alias] for alias, name in programmers.items()]
        choice = Listbox(lc, self.i, self.o, "Avrdude programmer picker listbox", selected=self.current_programmer).activate()
        if choice:
            self.current_programmer = choice
            self.config["default_programmer"] = self.current_programmer
            self.save_config()

    def set_bitclock(self):
        """
        Allows adjustments of avrdude bitclock, allowing to work with slowly-clocked
        microcontrollers.
        """
        bitclock = IntegerAdjustInput(self.bitclock, self.i, self.o, message="Bitclock:", name="Avrdude app bitclock adjust", min=1, max=50).activate()
        if bitclock:
            self.bitclock = bitclock
            self.config["last_bitclock"] = bitclock
            self.save_config()

    def toggle_filter_programmers(self):
        """
        Toggles whether the programmers in the programmer list are filtered
        (for user convenience).
        """
        self.filter_programmers = not self.filter_programmers
        self.config["filter_programmers"] = self.filter_programmers
        self.save_config()

    def settings_menu(self):
        def get_contents():
            return [["Set bitclock (-B)", self.set_bitclock],
                    #["Report last error", self.report_last_error],
                    ["Unfilter programmers" if self.filter_programmers else "Filter programmers", self.toggle_filter_programmers]]
        Menu([], self.i, self.o, contents_hook=get_contents, name="Avrdude app settings menu").activate()

    # User-friendliness

    def get_filtered_programmers(self, programmers):
        """
        A filtering function to only allow selecting programmers from a whitelist.
        """
        return {alias:name for alias, name in programmers.items() if alias in self.supported_programmers}

    def set_write_as_last_read(self):
        """
        A convenience function to set the write file as the target for read functions
        (to allow for convenient copying of microcontrollers).
        """
        self.write_file = os.path.join(self.read_dir, self.read_filename+".hex")
        self.write_params = []
        self.config["last_write_file"] = self.write_file
        self.config["last_write_fuse_params"] = self.write_fuse_params
        self.save_config()

    # Bugreport functions - TODO

    #def report_last_error(self):
    #    #Describe the report procedure
    #    #Ask for sending confirmation
    #    self.send_bugreport()

    #def send_bugreport(self):
    #    # use bugreport library
    #    bugreport = BugReport()
    #    if not hasattr(self, 'p') or not self.p:
    #        PrettyPrinter("No process found - nothing to send!", self.i, self.o, 3)
    #        return
    #    status = self.p.get_status()
    #    bugreport.add_text()
    #    bugreport.send()

    # Fuse file detection/format functions for write_checklist

    def autodetect_memory_files(self, write_file):
        """
        This function autodetects files that could've been written by app's
        read functions. They have the same filename as the write file,
        but a different extension (denoting their type).
        Returns [type, value, format] lists ready to be inserted into
        the avrdude commandline template.
        """
        files = [["flash", write_file, self.flash_format]]
        write_dir, write_filename = os.path.split(write_file)
        base_filename = write_filename.rsplit('.', 1)[0]
        # Get all files from the write directory
        wp_files = [file for file in os.listdir(write_dir) \
                            if os.path.isfile(os.path.join(write_dir, file))]
        # Split filenames and extensions
        wp_files_exts = [file.rsplit('.', 1) for file in wp_files]
        # Get all the files where filename matches the base filename and extension is supported
        suitable_files = [file for file in wp_files_exts if file[0] == base_filename \
                                                      and file[-1] in self.fuse_types \
                                                      and len(file) == 2 ]
        # Get the extensions from that list
        available_exts = [file[-1] for file in suitable_files]
        # "available_exts" is a subset of "self.fuse_types" now
        # building [type, value, format] lists
        for type in available_exts:
            value = os.path.join(write_dir, base_filename+'.'+type)
            files.append([type, value, self.fuse_format])
        return files
