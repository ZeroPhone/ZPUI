import importlib
import os
import traceback

from apps import zero_app
from helpers import setup_logger
from ui import Printer, Menu

logger = setup_logger(__name__, "info")


class ListWithMetadata(list):
    ordering_alias = None


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
    ordering_cache = {}

    def __init__(self, app_directory, i, o):
        self.app_directory = app_directory
        self.i = i
        self.o = o

    def load_all_apps(self):
        base_menu = Menu([], self.i, self.o, "Main app menu",
                                    exitable=False)  # Main menu for all applications.
        base_menu.exit_entry = ["Exit", "exit"]
        base_menu.process_contents()
        self.subdir_menus[self.app_directory] = base_menu
        for path, subdirs, modules in app_walk(self.app_directory):
            for subdir in subdirs:
                # First, we create subdir menus (not yet linking because they're not created in correct order) and put them in subdir_menus.
                subdir_path = os.path.join(path, subdir)
                self.subdir_menus[subdir_path] = Menu([], self.i, self.o, subdir_path)
            for _module in modules:
                # Then, we load modules and store them along with their paths
                try:
                    module_path = os.path.join(path, _module)
                    app = self.load_app(module_path)
                    logger.info("Loaded app {}".format(module_path))
                    self.app_list[module_path] = app
                except Exception as e:
                    logger.error("Failed to load app {}".format(module_path))
                    logger.error(traceback.format_exc())
                    Printer(["Failed to load", os.path.split(module_path)[1]], self.i, self.o, 2)
        for subdir_path in self.subdir_menus:
            # Now it's time to link menus to parent menus
            if subdir_path == self.app_directory:
                continue
            parent_path = os.path.split(subdir_path)[0]
            ordering = self.get_ordering(parent_path)
            parent_menu = self.subdir_menus[parent_path]
            subdir_menu = self.subdir_menus[subdir_path]
            subdir_menu_name = self.get_subdir_menu_name(subdir_path)
            # Inserting by the ordering given
            parent_menu_contents = self.insert_by_ordering([subdir_menu_name, subdir_menu.activate],
                                                           os.path.split(subdir_path)[1], parent_menu.contents,
                                                           ordering)
            parent_menu.set_contents(parent_menu_contents)
        for app_path in self.app_list:
            # Last thing is attaching applications to the menu structure created.
            app = self.app_list[app_path]
            subdir_path, app_dirname = os.path.split(app_path)
            ordering = self.get_ordering(subdir_path)
            menu_name = app.menu_name if hasattr(app, "menu_name") else app_dirname.capitalize()
            self.bind_callback(app, app_path, menu_name, ordering, subdir_path)
        return base_menu

    def bind_callback(self, app, app_path, menu_name, ordering, subdir_path):
        if hasattr(app, "callback") and callable(app.callback):  # for function based apps
            subdir_menu = self.subdir_menus[subdir_path]
            subdir_menu_contents = self.insert_by_ordering([menu_name, app.callback], os.path.split(app_path)[1],
                                                           subdir_menu.contents, ordering)
            subdir_menu.set_contents(subdir_menu_contents)
            return True
        if hasattr(app, "on_start") and callable(app.on_start):  # for class based apps
            subdir_menu = self.subdir_menus[subdir_path]
            subdir_menu_contents = self.insert_by_ordering([menu_name, app.on_start], os.path.split(app_path)[1],
                                                           subdir_menu.contents, ordering)
            subdir_menu.set_contents(subdir_menu_contents)
        else:
            logger.debug("App \"{}\" has no callback; loading silently".format(menu_name))

    def load_app(self, app_path):
        main_py_string = "/main.py"
        if app_path.endswith(main_py_string):
            app_path = app_path[:-len(main_py_string)]
        if "__init__.py" not in os.listdir(app_path):
            raise ImportError("Trying to import an app with no __init__.py in its folder!")
        app_import_path = app_path.replace('/', '.')
        # If user runs in single-app mode and by accident
        # autocompletes the app name too far, it shouldn't fail
        app = importlib.import_module(app_import_path + '.main', package='apps')
        if is_class_based_module(app):
            zero_app_subclass = get_zeroapp_class_in_module(app)
            app = zero_app_subclass(self.i, self.o)
        else:
            app.init_app(self.i, self.o)
        return app

    def get_subdir_menu_name(self, subdir_path):
        """This function gets a subdirectory path and imports __init__.py from it. It then gets _menu_name attribute from __init__.py and returns it. 
        If failed to either import __init__.py or get the _menu_name attribute, it returns the subdirectory name."""
        subdir_import_path = subdir_path.replace('/', '.')
        try:
            subdir_object = importlib.import_module(subdir_import_path + '.__init__')
            return subdir_object._menu_name
        except Exception as e:
            logger.error("Exception while loading __init__.py for subdir {}".format(subdir_path))
            logger.error(e)
            return os.path.split(subdir_path)[1].capitalize()

    def get_ordering(self, path):
        """This function gets a subdirectory path and imports __init__.py from it. It then gets _ordering attribute from __init__.py and returns it. It also caches the attribute for faster initialization.
        If failed to either import __init__.py or get the _ordering attribute, it returns an empty list."""
        if path in self.ordering_cache:
            return self.ordering_cache[path]
        import_path = path.replace('/', '.')
        ordering = []
        try:
            imported_module = importlib.import_module(import_path + '.__init__')
            ordering = imported_module._ordering
            logger.debug("Found ordering for {} directory!".format(import_path))
        except ImportError as e:
            logger.error("Exception while loading __init__.py for directory {}".format(path))
            logger.debug(e)
        except AttributeError as e:
            pass
        finally:
            self.ordering_cache[path] = ordering
            return ordering

    def insert_by_ordering(self, to_insert, alias, l, ordering):
        if alias in ordering:
            # HAAAAAAAAAAAAAAXXXXXXXXXX
            to_insert = ListWithMetadata(to_insert)
            # Marking the object we're inserting with its alias
            # so that we won't mix up ordering of elements later
            to_insert.ordering_alias = alias
            if not l:  # No conditions to check
                l.append(to_insert)
                return l
            for e in l:
                if hasattr(e, "ordering_alias"):
                    if ordering.index(e.ordering_alias) > ordering.index(alias):
                        l.insert(l.index(e), to_insert)
                        return l
                    else:
                        pass  # going to next element
                else:
                    l.insert(l.index(e), to_insert)
                    return l
        l.append(to_insert)
        return l  # Catch-all


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
            if issubclass(class_, zero_app.ZeroApp) and item != 'ZeroApp':
                return class_
        except Exception as e:
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
