import os
from time import sleep, time

from zpui_lib.ui import Canvas, Menu, open_image, invert_image, fit_image_to_dims, IntegerAdjustInput, Checkbox, TextReader
from zpui_lib.apps import ZeroApp
from zpui_lib.ui.base_ui import BaseUIElement
from zpui_lib.actions import ContextSwitchAction
from zpui_lib.helpers import ExitHelper, setup_logger, remove_left_failsafe, read_or_create_config, \
                             local_path_gen, save_config_method_gen, BooleanEvent, BackgroundRunner

# py2 compat? I forgot
try:
    from queue import Queue, Empty
except ModuleNotFoundError:
    from Queue import Queue
    Empty = Queue.Empty


from PIL import Image

local_path = local_path_gen(__name__)
logger = setup_logger(__name__, "warning")

default_accepted_extensions = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]

default_config = """enabled: true
timeout: 60
images: images/
global_invert: false
"""

class ScreensaverApp(ZeroApp):

    all_sources = ["input", "output"]

    def init_app(self):
        self.config = read_or_create_config(local_path("config.yaml"), default_config, "Screensaver app config")
        self.save_config = save_config_method_gen(self, local_path("config.yaml"))
        if self.config["images"].lstrip().startswith("/"): # abs path
            self.images_path = self.config["images"]
        else:
            self.images_path = local_path(self.config["images"])
        self.load_images(self.images_path)
        self.screensaver_br = None # for tracking whether the screensaver backgroundrunner has been set
        self.activity_queue = Queue()
        self.do_stop = BooleanEvent()
        self.inhibit_screensaver = BooleanEvent()

    def load_images(self, images_path=None):
        # default parameter to be able to run this function from a Menu
        if images_path == None: images_path = self.images_path
        self.images = {}
        accepted_extensions = set(default_accepted_extensions+self.config.get("accepted_extensions", []))
        logger.debug(f"Loading images from {self.images_path}")
        if not os.path.isdir(images_path):
            logger.error(f"Directory {images_path} non-existent?")
            return
        for name in os.listdir(images_path):
            if os.path.isfile(os.path.join(images_path, name)) and any([name.endswith(extension) for extension in accepted_extensions]):
                full_path = os.path.join(images_path, name)
                try:
                    image = open_image(full_path)
                except:
                    logger.exception(f"Failed to load image from {full_path}!")
                else:
                    logger.debug(f"Loaded image from {full_path}")
                    self.images[full_path] = image
            else:
                logger.debug(f"Ignoring file '{name}'")
        self.process_images()

    def set_context(self, c):
        self.context = c
        c.threaded = False
        #c.set_target(self.activate_screensaver)
        c.register_action(ContextSwitchAction("screensaver", c.request_switch, menu_name="Screensaver", description="Switches to the screensaver app"))
        c.set_provider("settings_screensaver", self.settings_screensaver)
        c.activity_hook = self.activity_hook
        result = c.request_activity_cb()
        if not result:
            logger.error("Request activity cb context action refused!")

    def execute_after_contexts(self):
        # let's only start the screensaver after all other apps are mostly-loaded
        self.activate_screensaver_thread()

    def activity_hook(self, source, **data):
        allowed_sources = self.config.get("allowed_sources", self.all_sources)
        if source in allowed_sources:
            logger.debug(f"Screensaver activity: {source} {data}")
            self.activity_queue.put((source, data))
        else:
            logger.debug(f"Ignoring activity from disallowed source {source} {data}")

    def settings_screensaver(self):
        def get_mc():
            mc = [
                ["Screensaver: {}".format("ON" if self.config.get("enabled", True) else "OFF"), self.toggle_enabled],
                ["Timeout: {}".format(self.config.get("timeout", 300)), self.set_timeout],
                ["Sources: {}".format(", ".join(self.config.get("allowed_sources", self.all_sources))), self.configure_sources],
                ["Rescan directory", self.load_images],
                ["Exclude images", self.exclude_images_menu],
                ["Invert images", self.invert_images_menu],
                ["Global invert: {}".format("ON" if self.config.get("global_invert", False) else "OFF"), self.toggle_global_invert],
                ["Attribution", self.show_attribution],
            ]
            return mc
        self.inhibit_screensaver.set()
        Menu([], self.i, self.o, contents_hook=get_mc, name="Screensaver settings menu").activate()
        self.inhibit_screensaver.clear()

    settings_screensaver.name = "Screensaver settings"

    def show_attribution(self):
        text = """# Credits
        Images by WifiCable"""
        TextReader(text, self.i, self.o, name="Screensaver credits textreader").activate()

    def configure_sources(self):
        current_sources = self.config.get("allowed_sources", self.all_sources)
        cbc = [[name.capitalize(), name, name in current_sources] for name in self.all_sources]
        choices = Checkbox(cbc, self.i, self.o, name="Screensaver source listbox").activate()
        if choices:
            self.config["allowed_sources"] = [name for name in self.all_sources if choices[name]]
            self.save_config()

    def set_timeout(self):
        timeout = self.config.get("timeout", 300)
        self.config["timeout"] = timeout
        answer = IntegerAdjustInput(timeout, self.i, self.o, interval=10, min=10, name="Screensaver timeout adjuster").activate()
        if answer:
            self.config["timeout"] = answer
            self.save_config()

    def toggle_global_invert(self):
        self.config["global_invert"] = not self.config.get("global_invert", False)
        self.save_config()
        self.process_images()

    def toggle_enabled(self):
        self.config["enabled"] = not self.config.get("enabled", True)
        if self.config["enabled"]:
            # starting if it was stopped
            self.activate_screensaver_thread()
        else:
            if self.do_stop != None:
                self.do_stop.set(True)
        self.save_config()

    def invert_images_menu(self):
        inverted_images = self.config.get("inverted_images", [])
        self.config["inverted_images"] = inverted_images # making sure it's present
        def toggle_inverted(path):
            if path in self.config["inverted_images"]: self.config["inverted_images"].remove(path)
            elif path not in self.config["inverted_images"]: self.config["inverted_images"].append(path)
            self.process_images()
            self.save_config()
        def get_mc():
            mc = []
            for path in self.images:
                inverted =  path in self.config["inverted_images"]
                dir, name = os.path.split(path)
                menu_text = "{}{}({})".format("*" if inverted else " ", name, dir)
                mc.append([menu_text, lambda x=path: toggle_inverted(x)])
            return mc
        Menu([], self.i, self.o, contents_hook=get_mc, name="Screensaver settings inverted images menu").activate()

    def exclude_images_menu(self):
        excluded_images = self.config.get("excluded_images", [])
        self.config["excluded_images"] = excluded_images # making sure it's present
        def toggle_excluded(path):
            if path in self.config["excluded_images"]: self.config["excluded_images"].remove(path)
            elif path not in self.config["excluded_images"]: self.config["excluded_images"].append(path)
            self.process_images()
            self.save_config()
        def get_mc():
            mc = []
            for path in self.images:
                excluded =  path in self.config["excluded_images"]
                dir, name = os.path.split(path)
                menu_text = "{}{}({})".format("*" if excluded else " ", name, dir)
                mc.append([menu_text, lambda x=path: toggle_excluded(x)])
            return mc
        Menu([], self.i, self.o, contents_hook=get_mc, name="Screensaver settings excluded images menu").activate()

    def process_images(self):
        self.processed_images = {}
        for path, image in self.images.items():
            if path in self.config.get("excluded_images", []):
                continue
            try:
                if "color" not in self.o.type:
                    # let's try and dither the image for a b&w screen
                    image = image.convert(self.o.device_mode, dither=Image.Dither.FLOYDSTEINBERG)
                else:
                    image = image.convert(self.o.device_mode)
                if self.config.get("global_invert", False):
                    try:
                        image = invert_image(image)
                    except:
                        logger.exception(f"Failed to invert image {path}!")
                        break
                if path in self.config.get("inverted_images", []):
                    # this will double-invert some images during global invert, which is probably fine?
                    try:
                        image = invert_image(image)
                    except:
                        logger.exception(f"Failed to invert image {path}!")
                        continue
                if image.size != (self.o.width, self.o.height):
                    logger.debug("{} {} ".format(path, image.size, (self.o.width, self.o.height)))
                    image = fit_image_to_dims(image, self.o.width, self.o.height, fill_color=Canvas(self.o).background_color)
            except:
                logger.exception(f"Failed to process image {path}")
            else:
                self.processed_images[path] = image

    def activate_screensaver_thread(self):
        if self.screensaver_br and not self.screensaver_br.finished and not self.screensaver_br.failed:
            for i in range(5):
                sleep(1)
                if self.screensaver_br.finished or self.screensaver_br.failed:
                    break
            return False
        self.do_stop.clear()
        self.screensaver_br = BackgroundRunner(self.screensaver_thread, do_stop=self.do_stop)
        self.screensaver_br.run()

    def screensaver_thread(self, do_stop=None):
        logger.info("Screensaver thread started")
        self.activated = BooleanEvent()
        self.last_activity_time = time()
        while self.config.get("enabled", True):
            if do_stop: return
            item = None
            try:
                item = self.activity_queue.get(False, 0.1)
            except Empty:
                sleep(1)
                if do_stop: return
            except AttributeError:
                pass
            except:
                logger.exception("Unknown error getting data from queue!")
                self.do_stop.set()
            else:
                source, data = item
                self.last_activity_time = time()
                if source == "input":
                    if self.activated:
                        self.activated.clear()
                        self.context.signal_finished()
                        logger.info("Screensaver deactivated")
                        # Currently processign all input actions the same
                        #action = data.get("action", "regular")
                        """
                        if action in ["global", "nonmaskable", "backlight_on"]:
                        elif action in ["regular", "maskable", "streaming", "unhandled"]:
                        """
                    else:
                        # not activated, and already timestamped - just ignore
                        pass
            # now we check if screensaver should be activated, and activate if activity timeout exceeded
            if time() - self.last_activity_time > self.config.get("timeout", 300) and not self.activated:
                if not self.inhibit_screensaver:
                    self.o.display_image(self.processed_images[list(self.processed_images.keys())[0]])
                    if not self.context.request_switch():
                        logger.error("Can't switch to context!")
                    else:
                        logger.debug("Context switched!")
                        self.activated.set()
                        logger.info("Screensaver activated")
                else:
                    # inhibited, we're probably in screensaver settings. which makes this simple code freak out lol
                    sleep(1)
