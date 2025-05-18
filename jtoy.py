import json
import yaml
import sys
import os
# migrations
# 1. remove kwargs from i/o config for config readability
# 2. shorten configs if necessary - to a single dict instead of [dict], or even to a name if kwargs is not provided
# 3. remove backlight_interval:10 old default argument, since it's no longer relevant

def yeet_kwargs(config, section):
    if section in config:
        if isinstance(config[section], str):
            # good, it's a string. nobody is using this feature at the time of recording just yet lmao
            # there's also no kwargs to be found
            return config
        if isinstance(config[section], list):
            drivers = config[section] # a little quick normalization
        else:
            drivers = [config[section]]
        for driver in drivers:
            if "kwargs" in driver:
                # a config readability fix
                kw = driver.get("kwargs")
                # check for key conflicts
                if not any([key in driver for key in kw]):
                    driver.pop("kwargs")
                    driver.update(kw)
        # now, shortening the config
        for i, driver in enumerate(config[section]):
            # now-unused default key, yeetable
            if driver.get("backlight_interval", None) == 10:
                driver.pop("backlight_interval")
            if len(driver.keys()) == 1:
                # just replacing with name
                config[section][i] = driver["driver"]
        # just one driver? yeet the list
        if len(config[section]) == 1:
            config[section] = config[section][0]
    return config # not necessary cuz mutability but hey

if __name__ == "__main__":
    filename_supplied = False
    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]):
            filename_supplied = True
            with open(sys.argv[1]) as f:
                config = json.load(f)
        else:
            config = json.loads(sys.argv[1])
    else:
        with open("config.json") as f:
            config = json.load(f)
    #print(config)

    config = yeet_kwargs(config, "input")
    config = yeet_kwargs(config, "output")
    #print(config)
    # final export
    if len(sys.argv) > 1:
        if filename_supplied:
            print(yaml.safe_dump(config))
        else:
            print(repr(yaml.safe_dump(config)))
    else:
        with open("config.yaml", 'w') as f:
            yaml.safe_dump(config, f)
        print(yaml.safe_dump(config))
