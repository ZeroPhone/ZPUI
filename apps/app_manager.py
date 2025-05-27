import importlib
import os
import sys
import traceback

from apps import ZeroApp
from zpui_lib.helpers import setup_logger, zpui_running_as_service
from ui import Printer, Menu, HelpOverlay, GridMenu, Entry, \
               GridMenuLabelOverlay, GridMenuSidebarOverlay, GridMenuNavOverlay

from PIL import Image, ImageOps

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


logger = setup_logger(__name__, "info")


class AppManager(object):
    subdir_menus = {}
    """ Example of subdir_menus:
    {'apps/network_apps': <ui.menu.Menu instance at 0x7698ac10>,
    ...
    'apps/system_apps': <ui.menu.Menu instance at 0x7698abc0>}
    """
    app_list = {}
    """Example of app_list:
    {'apps/network_apps/wpa_cli': <module 'apps.network_apps.wpa_cli.main' from '/root/WCS/apps/network_apps/wpa_cli/main.py'>, 
    'apps/system_apps/system': <module 'apps.system_apps.system.main' from '/root/WCS/apps/system_apps/system/main.py'>, 
    ...
    'apps/network_apps/network': <module 'apps.network_apps.network.main' from '/root/WCS/apps/network_apps/network/main.py'>}
     """
    failed_apps = {}
    """Example of failed_apps:
    {'apps/network_apps/wpa_cli': "Traceback: \n ...."
    }
    """
    ordering_cache = {}

    def __init__(self, app_directory, context_manager, config=None, default_plugins=True):
        self.subdir_menus = {}
        self.subdir_menu_contents = {}
        self.subdir_menu_creators = {}
        self.subdir_menu_overlays = {}
        self.subdir_paths = []
        self.app_list = {}
        self.failed_apps = {}
        self.app_directory = app_directory
        self.cm = context_manager
        self.i, self.o = self.cm.get_io_for_context("main")
        self.config = config if config else {}
        #logger.warning(self.config)
        if default_plugins and self.config.get("default_overlays", True):
            self.register_default_plugins()

    def create_main_menu(self, menu_name, contents):
        dir = "resources/icons/"
        icons = [f for f in os.listdir(dir) if f.endswith(".png")]
        icon_paths = {f.rsplit('.', 1)[0]:os.path.join(dir, f) for f in icons}
        used_icons = []
        for entry in contents:
            for icon_name, icon_path in icon_paths.items():
                if entry.basename.startswith(icon_name):
                    entry.icon = Image.open(icon_path)
                    used_icons.append(icon_name)
                    continue
            else:
                pass
        if zpui_running_as_service():
            exit_entry = Entry("Restart ZPUI", "exit", icon=Image.open(icon_paths["exit"]))
        else:
            exit_entry = Entry("Exit", "exit", icon=Image.open(icon_paths["exit"]))
        #print([x for x, y, in icon_paths if x not in used_icons])
        font = ("Fixedsys62.ttf", 16)
        menu = GridMenu(contents, self.i, self.o, font=font, name="Main menu", exitable=False, navigation_wrap=False)
        menu.exit_entry = exit_entry
        menu.process_contents()
        return menu

    def sidebar_cb(self, c, ui_el, coords):
        sidebar_image = ImageOps.invert(Image.open("resources/sidebar.png").convert('L'))
        sidebar_image.convert(c.o.device_mode)
        c.image.paste(sidebar_image, (coords.left+3, coords.top-5))

    def overlay_main_menu(self, menu):
        #main_menu_help = "ZPUI main menu. Navigate the folders to get to different apps, or press KEY_PROG2 (anywhere in ZPUI) to get to the context menu."
        GridMenuNavOverlay().apply_to(menu)
        if menu.view.sidebar_fits:
            GridMenuSidebarOverlay(self.sidebar_cb).apply_to(menu)
        if not getattr(menu.view, "shows_label", False):
            GridMenuLabelOverlay().apply_to(menu)
        #HelpOverlay(main_menu_help).apply_to(menu)

    def register_default_plugins(self):
        self.subdir_menu_creators["apps"] = self.create_main_menu
        self.subdir_menu_overlays["apps"] = [self.overlay_main_menu]

    def create_subdir_menu(self, menu_name, contents):
        menu = Menu(contents, self.i, self.o, "Subdir menu ({})".format(menu_name))
        return menu

    def create_menu_structure(self):
        base_subdir = self.app_directory.rstrip('/')
        for subdir_path in self.subdir_paths:
            self.subdir_menu_contents[subdir_path] = []
        # ordering by path length so that the longest-path (innermost) directories are in the beginning of the list
        self.subdir_paths = sorted(self.subdir_paths, key=lambda x:-1*len(x))
        for subdir_path in self.subdir_paths:
            if subdir_path == base_subdir:
                continue
            parent_path = os.path.split(subdir_path)[0]
            menu_name = self.get_subdir_menu_name(subdir_path)
            subdir_entry = Entry(menu_name, type="dir", path=subdir_path)
            self.subdir_menu_contents[parent_path].append(subdir_entry)
        subdir_menu_paths = self.subdir_menu_contents.keys()
        for app_path, app_obj in self.app_list.items():
            if self.app_has_callback(app_obj):
                try:
                    subdir_menu_name = max([n for n in subdir_menu_paths if app_path.startswith(n)])
                    menu_name = self.get_app_name(app_obj, app_path)
                    app_entry = Entry(menu_name, type="app", obj=app_obj, path=app_path)
                    self.subdir_menu_contents[subdir_menu_name].append(app_entry)
                except:
                    logger.exception("Couldn't place app {} into a menu!".format(app_path))
        # now, filtering for empty directories, removing directories up until we're satisfied that none are empty
        success = False
        iters = 0
        empty_dirs = []
        while not success:
            sbmc_items = list(self.subdir_menu_contents.items())
            # again, sorting by path length to process innermost directories first
            # example: subdir_entry = Entry(menu_name, type="dir", path=subdir_path)
            sbmc_items = sorted(sbmc_items, key=lambda x:-1*len(x[0]))
            success = True
            if iters > 10:
                logger.error("Too many iterations taken to filter out the menu from empty items, breaking the loop")
                break
            for path, subdir_contents in sbmc_items:
                for entry in subdir_contents:
                    if entry.path in empty_dirs:
                        logger.debug("Empty dir {} found in menu for {}, removing".format(entry.path, path))
                        self.subdir_menu_contents[path].remove(entry)
                        success = False
                if not subdir_contents:
                    success = False
                    empty_dirs.append(path)
                    self.subdir_menu_contents.pop(path)
            iters += 1
        if empty_dirs:
            logger.info("Removed empty directories: {}".format(", ".join(empty_dirs)))
        for path, subdir_contents in self.subdir_menu_contents.items():
            ordering = self.get_ordering(path)
            unordered_contents = self.prepare_menu_contents_for_ordering(subdir_contents)
            menu_contents = self.order_contents_by_ordering(unordered_contents, ordering)
            creator = self.subdir_menu_creators.get(path, self.create_subdir_menu)
            menu = creator(path, menu_contents)
            for overlay_cb in self.subdir_menu_overlays.get(path, []):
                overlay_cb(menu)
            self.subdir_menus[path] = menu
        return self.subdir_menus[base_subdir]

    def prepare_menu_contents_for_ordering(self, subdir_contents):
        for entry in subdir_contents:
            entry.basename = os.path.split(entry.path)[-1]
            if entry.type == "dir":
                entry.cb = lambda x=entry.path: self.switch_to_subdir(x)
            elif entry.type == "app":
                entry.cb = lambda x=entry.path: self.switch_to_app(x)
        return subdir_contents

    def switch_to_subdir(self, path):
        self.subdir_menus[path].activate()

    def switch_to_app(self, path):
        self.cm.switch_to_context(path.replace("/", '.'))

    def order_contents_by_ordering(self, contents, ordering, strip_first_element=True):
        if ordering:
            contents = sorted(contents, key=lambda x: ordering.index(x.basename) if x.basename in ordering else 9999)
        return contents

    def load_all_apps(self, interactive=True):
        apps_blocked_in_config = self.config.get("do_not_load", [])
        self.subdir_paths.append(self.app_directory.rstrip("/"))
        # first: directory-based discovery
        for path, subdirs, modules in app_walk(self.app_directory):
            for subdir in subdirs:
                subdir_path = os.path.join(path, subdir)
                self.subdir_paths.append(subdir_path)
            # apps having an "execute_after_contexts" hook
            after_contexts_apps = {}
            for _module in modules:
                module_path = os.path.join(path, _module)
                try:
                    if module_path in apps_blocked_in_config:
                        logger.warning("App {} blocked from config; not loading".format(module_path))
                        continue
                    app = self.load_app_by_path(module_path)
                    has_loaded = True; s = ""
                    if hasattr(app, "can_load"):
                        result = app.can_load()
                        if result != True: # likely, a list of things has been returned
                            if result == None:
                                logger.warning("App {} returned None from can_load! Assuming True".format(module_path))
                            else:
                                has_loaded, s = result
                    if has_loaded:
                        logger.info("Loaded app {}".format(module_path))
                        self.app_list[module_path] = app
                        menu_name = self.get_app_name(app, module_path)
                        self.bind_context(app, module_path, menu_name)
                        if self.app_has_after_contexts_hook(app):
                            after_contexts_apps[module_path] = app
                    else:
                        self.mark_app_as_unloaded(app, module_path, s)
                except:
                    logger.exception("Failed to load app {}".format(module_path))
                    self.failed_apps[module_path] = traceback.format_exc()
            if interactive:
                if self.failed_apps:
                    failed_app_names = [os.path.split(p)[1] for p in self.failed_apps.keys()]
                    Printer(["Failed to load:"]+failed_app_names, self.i, self.o, 0.5)
            # execute after_context functions
            for app_path, app in after_contexts_apps.items():
                try:
                    self.execute_after_contexts(app)
                except:
                    logger.exception("Failed to execute 'after all contexts' hook for {}".format(app_path))
                else:
                    logger.info("Executed 'after all contexts' hook for {}".format(app_path))
        # second: entrypoint-based discovery
        discovered_apps = entry_points(group='spam.magical')
        for app_ep in discovered_apps:
            logger.info(str(app_ep))
            try:
                app = app_ep.load()
            except:
                logger.exception("Failing to load entrypoint for external app {}".format(app_ep))
                continue
            app_name = app_ep.name
            try:
                module_path = getattr(app, "module_path", app_name)
                if not module_path.startswith("apps"):
                    if not module_path.startswith('/'): module_path = '/'+module_path
                    module_path = "apps"+module_path
                # here we add the subdir path(s) if path(s) not yet known
                subdir_path = module_path
                if subdir_path.endswith(app_name):
                    subdir_path = subdir_path[:-(len(app_name))]
                # adding recursively
                subdir_path_els = subdir_path.split("/")
                for element_len in range(len(subdir_path_els)-1):
                    this_subdir_path = "/".join(subdir_path_els[:element_len+1])
                    if this_subdir_path not in self.subdir_paths:
                        self.subdir_paths.append(this_subdir_path)
                # now, we make sure that module path ends with app name
                if not module_path.endswith(app_name):
                    if not module_path.endswith('/'): module_path += '/'
                    module_path += app_name
            except:
                logger.exception("Can't get module_path or add subdir for external app {}".format(app_ep))
                continue
            try:
                loaded_app = self.load_app(app, app_path=module_path)
                logger.info("Loaded external app {}".format(module_path))
                self.app_list[module_path] = app
                menu_name = self.get_app_name(app, module_path)
                self.bind_context(app, module_path, menu_name)
                if self.app_has_after_contexts_hook(app):
                    after_contexts_apps[module_path] = app
            except:
                logger.exception("Failed to load external app {}".format(module_path))
        base_menu = self.create_menu_structure()
        return base_menu

    def app_has_callback(self, app):
        return (hasattr(app, "callback") and callable(app.callback)) or \
               (hasattr(app, "on_start") and callable(app.on_start))

    def bind_context(self, app, path, menu_name):
        if hasattr(app, "callback") and callable(app.callback):  # for function based apps
            app_callback = app.callback
        elif hasattr(app, "on_start") and callable(app.on_start):  # for class based apps
            app_callback = app.on_start
        else:
            logger.debug("App \"{}\" has no callback; loading silently".format(menu_name))
            return
        app_path = path.replace('/', '.')
        self.cm.register_context_target(app_path, app_callback)
        self.cm.set_menu_name(app_path, menu_name)

    def execute_after_contexts(self, app):
        app.execute_after_contexts()

    def app_has_after_contexts_hook(self, app):
        """
        Checks whether the app has "execute after all contexts
        are loaded" hook. A separate method for ease of future
        changes.
        """
        return hasattr(app, "execute_after_contexts")

    def get_app_path_for_cmdline(self, cmdline_app_path):
        main_py_string = "/main.py"
        if cmdline_app_path.endswith(main_py_string):
            app_path = cmdline_app_path[:-len(main_py_string)]
        elif cmdline_app_path.endswith("/"):
            app_path = cmdline_app_path[:-1]
        else:
            app_path = cmdline_app_path
        return app_path

    def load_single_app_by_path(self, app_path, threaded = True):
        # If user runs in single-app mode and by accident
        # autocompletes the app name too far, it shouldn't fail
        app_path = self.get_app_path_for_cmdline(app_path)
        if "__init__.py" not in os.listdir(app_path):
            raise ImportError("Trying to import an app ({}) with no __init__.py in its folder!".format(app_path))
        app_import_path = app_path.replace('/', '.')
        app = self.load_app_by_path(app_import_path, threaded=threaded)
        return app_import_path, app

    def load_app_by_path(self, path, threaded=True):
        app_path = path.replace('/', '.')
        app = importlib.import_module(app_path + '.main', package='apps')
        return self.load_app(app, app_path=app_path, threaded=threaded)

    def load_app(self, app, app_path=None, threaded=True):
        app_path = app_path.replace('/', '.') # just in case lol
        context = self.cm.create_context(app_path)
        context.threaded = threaded
        i, o = self.cm.get_io_for_context(app_path)
        if is_class_based_module(app):
            app_class = get_zeroapp_class_in_module(app)
            app = app_class(i, o)
        else:
            if hasattr(app, 'init_app'):
                app.init_app(i, o)
            else: #init_app-less function-based app
                app.i = i
                app.o = o
        self.pass_context_to_app(app, app_path, context)
        return app

    def mark_app_as_unloaded(self, app, app_path, s):
        logger.info("App {} not loaded. Reason given: {}".format(app_path, repr(s)))

    def pass_context_to_app(self, app, app_path, context):
        """
        This is a function to pass context objects to apps. For now, it works
        with both class-based and module-based apps. It only passes the context
        if it detects that the app has the appropriate function to do that.
        """
        if hasattr(app, "set_context") and callable(app.set_context):
            try:
                app.set_context(context)
            except Exception as e:
                logger.exception("App {}: app class has 'set_context' but raised exception when passed a context".format(app_path))
            else:
                logger.debug("Passed context to app {}".format(app_path))

    def get_app_name(self, app, app_path):
        if hasattr(app, "menu_name"):
            return app.menu_name
        else:
            menu_name = os.path.split(app_path)[-1].capitalize().replace("_", " ")
            app.menu_name = menu_name
            return menu_name

    def get_subdir_menu_name(self, subdir_path):
        """
        This function gets a subdirectory path and imports __init__.py from it.
        It then gets _menu_name attribute from __init__.py and returns it.
        If failed to either import __init__.py or get the _menu_name attribute,
        it returns the subdirectory name.
        """
        # let's not load this if the dir doesn't actually exist)
        if not os.path.exists(subdir_path):
            logger.info("Not loading subdir menu name for dir that doesn't exist: {}".format(subdir_path))
            return os.path.split(subdir_path)[1].capitalize().replace("_", " ")
        subdir_import_path = subdir_path.replace('/', '.')
        try:
            subdir_object = importlib.import_module(subdir_import_path + '.__init__')
            return subdir_object._menu_name
        except:
            logger.exception("Exception while loading __init__.py for subdir {}".format(subdir_path))
            return os.path.split(subdir_path)[1].capitalize().replace("_", " ")

    def get_ordering(self, path):
        """This function gets a subdirectory path and imports __init__.py from it. It then gets _ordering attribute from __init__.py and returns it. It also caches the attribute for faster initialization.
        If failed to either import __init__.py or get the _ordering attribute, it returns an empty list."""
        if path in self.ordering_cache:
            return self.ordering_cache[path]
        import_path = path.replace('/', '.')
        ordering = []
        if not os.path.exists(path):
            # debug because we'll already have produced an identical exception in get_subdir_menu_name
            logger.debug("Not loading subdir menu name for dir that doesn't exist: {}".format(path))
        else:
            try:
                imported_module = importlib.import_module(import_path + '.__init__')
                ordering = imported_module._ordering
                logger.debug("Found ordering for {} directory!".format(import_path))
            except ImportError as e:
                logger.error("Exception while loading __init__.py for directory {}".format(path))
                logger.debug(traceback.format_exc())
            except AttributeError as e:
                pass
        self.ordering_cache[path] = ordering
        return ordering


def app_walk(base_dir):
    """Example of app_walk(directory):
    [('./apps', ['ee_apps', 'media_apps', 'test', 'system_apps', 'skeleton', 'network_apps'], ['__init__.pyc', '__init__.py']),
    ('./apps/ee_apps', ['i2ctools'], ['__init__.pyc', '__init__.py']),
    ('./apps/ee_apps/i2ctools', [], ['__init__.pyc', '__init__.py', 'main.pyc', 'main.py']),
    ('./apps/media_apps', ['mocp', 'volume'], ['__init__.pyc', '__init__.py']),
    ('./apps/media_apps/mocp', [], ['__init__.pyc', '__init__.py', 'main.pyc', 'main.py']),
    ('./apps/media_apps/volume', [], ['__init__.pyc', '__init__.py', 'main.pyc', 'main.py'])]
    """
    walk_results = []
    modules = []
    subdirs = []
    for element in os.listdir(base_dir):
        full_path = os.path.join(base_dir, element)
        if os.path.isdir(full_path):
            if is_subdir(full_path):
                subdirs.append(element)
                results = app_walk(full_path)
                for result in results:
                    walk_results.append(result)
            elif is_module_dir(full_path):
                modules.append(element)
    walk_results.append((base_dir, subdirs, modules))
    return walk_results


def get_zeroapp_class_in_module(module_):
    if 'init_app' in dir(module_):
        return None
    module_content = [item for item in dir(module_) if not item.startswith('__')]
    for item in module_content:
        class_ = getattr(module_, item)
        try:
            if issubclass(class_, ZeroApp):
                if item != 'ZeroApp':
                    return class_
        except TypeError:
            pass  # not a class : ignore
    return None


def is_class_based_module(module_):
    return get_zeroapp_class_in_module(module_) is not None


def is_module_dir(dir_path):
    contents = os.listdir(dir_path)
    return "main.py" in contents and "do_not_load" not in contents


def is_subdir(dir_path):
    contents = os.listdir(dir_path)
    return "__init__.py" in contents and "main.py" not in contents and "do_not_load" not in contents


if __name__ == "__main__":
    from mock import Mock
    cm = Mock()
    cm.configure_mock(get_io_for_context=lambda x: (x, x))
    am = AppManager("apps/", cm)
    am.o = Mock()
    am.o.configure_mock(cols=20, rows=8, char_width=6, width=128, height=64, device_mode='1', type=["b&w"])
    am.load_all_apps(interactive=False)
