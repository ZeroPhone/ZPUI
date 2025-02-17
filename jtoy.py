import json
import yaml
with open("config.json") as f:
    config = json.load(f)
print(config)
# migrations
# 1. remove kwargs from i/o config for config readability

def yeet_kwargs(config, section):
    if section in config:
        if isinstance(config[section], str):
            # good, it's a string. nobody is using this feature at the time of recording just yet lmao
            drivers = config[section]
        if isinstance(config[section], list):
            drivers = config[section]
        else:
            drivers = [config[section]]
        for driver in drivers:
            if "kwargs" in driver:
                # a config readability fix
                kw = driver.get("kwargs")
                # check for key conflicts
                if not any([key in driver for key in kw]):
                    config[section].update(kw)
    return config # not necessary cuz mutability but hey

config = yeet_kwargs(config, "input")
config = yeet_kwargs(config, "output")
print(config)
# final export
with open("config.yaml", 'w') as f:
    yaml.safe_dump(config, f)
