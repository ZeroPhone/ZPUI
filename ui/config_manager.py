import os
import json
import traceback
import collections

from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, "warning")

_UI_CONFIG_MANAGER = None

def get_ui_config_manager():
    global _UI_CONFIG_MANAGER
    if not _UI_CONFIG_MANAGER:
        _UI_CONFIG_MANAGER = UIConfigManager()
    return _UI_CONFIG_MANAGER


class UIConfigManager(object):
    base_config_name = "base_config.json"
    user_config_prefix = "config"
    user_config_postfix = ".json"

    global_config = None
    path = None

    def __init__(self):
        pass

    def set_path(self, path):
        self.path = path
        self.global_config = None #If path changes, global config is no longer valid

    def get_global_config(self):
        if not self.global_config:
            self.load_all_configs(self.path)
        return self.global_config

    def update_config(self, base_config, new_config):
        #Taken from https://stackoverflow.com/a/18394648/1250228
        #TODO: add some logging here, to show when base config 
        #items are being replaced
        for key, val in new_config.items():
            if isinstance(val, collections.abc.Mapping):
                tmp = self.update_config(base_config.get(key, { }), val)
                base_config[key] = tmp
            #Lists are not expected yet
            #elif isinstance(val, list):
            #    base_config[key] = (base_config.get(key, []) + val)
            else:
                base_config[key] = new_config[key]
        return base_config

    def load_all_configs(self, path):
        files = os.listdir(path)
        if self.base_config_name not in files:
            raise Exception("Base config not found!")
            #TODO: add fallback config!
        file_path = os.path.join(path, self.base_config_name)
        try:
            base_config = self.load_config(file_path)
        except Exception as e:
            logger.error("Exception while loading base config {}!".format(file_path))
            logger.exception(e)
            base_config = {}
        user_configs = []
        for file in files:
            if file.startswith(self.user_config_prefix) and \
                      file.endswith(self.user_config_postfix):
                user_configs.append(file)
        for file in user_configs:
            file_path = os.path.join(path, file)
            try:
                config = self.load_config(file_path)
            except Exception as e:
                logger.error("Exception while loading {} config".format(file_path))
                logger.exception(e)
            else:
                base_config = self.update_config(base_config, config)
        self.global_config = base_config

    def load_config(self, path):
        with open(path, "r") as f:
            result = json.load(f)
        return result
