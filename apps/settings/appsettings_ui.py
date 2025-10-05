i = None
o = None
cm = None
context = None

import zpui_lib.helpers.logger as log_system
from zpui_lib.ui import Menu, TextReader
from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "debug")

def get_menu_contents():
    settings_prefix = "settings_"
    providers = context.get_providers_by_type(settings_prefix)
    logger.debug("Settings providers: {}".format(providers))
    mc = []
    if cm != None:
        for name, provider in providers.items():
            pp = context.get_provider_provider(name)
            if pp == None: break # should not happen, but hey
            def cb():
                cm.switch_to_context(pp, func=provider)
            mc.append([provider.name, cb])
    else:
        logger.error("CM failed to bind, will not be able to switch to contexts!")
    mc.append(["Failed apps", failed_apps])
    mc.append(["Non-loaded apps", nonloaded_apps])
    return mc

def config_apps():
    Menu([], i, o, contents_hook=get_menu_contents, name="App settings main menu").activate()

def failed_apps():
    providers = context.get_providers_by_type("appmanager_")
    provider = context.get_provider("appmanager_failed")
    if provider:
        apps = provider()
        mc = []
        for app_path, reason in apps.items():
            text = "App {} failed to load. Traceback: \"{}\"".format(app_path, reason)
            tr = TextReader(text, i, o, name="Textreader for failed app {}".format(app_path))
            mc.append([app_path, tr.activate])
        if not mc:
            mc = [["No failed apps!", TextReader("yippie!!!", i, o, name="Textreader for no failed apps").activate]]
        Menu(mc, i, o, name="App settings failed apps menu").activate()

def nonloaded_apps():
    providers = context.get_providers_by_type("appmanager_")
    provider = context.get_provider("appmanager_nonloaded")
    if provider:
        apps = provider()
        mc = []
        for app_path, data in apps.items():
            name, reason = data
            text = "App {} ({}) not loaded. Reason: \"{}\"".format(name, app_path, reason)
            tr = TextReader(text, i, o, name="Textreader for nonloaded app {}".format(app_path))
            mc.append([name, tr.activate])
        if not mc:
            mc = [["No non-loaded apps!", TextReader("yippie!!!", i, o, name="Textreader for no nonloaded apps").activate]]
        Menu(mc, i, o, name="App settings nonloaded apps menu").activate()
