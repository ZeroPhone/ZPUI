#!/usr/bin/env python3

import traceback
import yaml
import sys

import hw_combos

grey = "\x1b[38;20m"
yellow = "\x1b[33;20m"
red = "\x1b[31;20m"
bold_red = "\x1b[31;1m"
reset = "\x1b[0m"

if __name__ == "__main__":
    filename = "config.yaml" if len(sys.argv) < 2 else sys.argv[1]

    try:
        with open(filename, 'r') as f:
            contents = f.read()
            f.seek(0)
            config = yaml.safe_load(f)
    except:
        print("Failed to parse YAML!")
        print(red, end=''); sys.stdout.flush()
        traceback.print_exc()
        print(reset, end=''); sys.stdout.flush()
        sys.exit(1)
    try:
        input_config, output_config, device = hw_combos.get_io_configs(config)
    except:
        print("Failed to interpret the configuration!")
        print(red, end=''); sys.stdout.flush()
        traceback.print_exc()
        print(reset, end=''); sys.stdout.flush()
        sys.exit(2)
    print(f"`{filename}` contents:\n{yellow}{contents.rstrip()}{reset}\n")
    if device:
        print(f"Parsed config for {device}: \n  {yellow}{config}{reset}")
    else:
        print(f"Parsed config: \n{yellow}{config}{reset}")
    print(f"Input device config: \n  {yellow}{input_config}{reset}")
    print(f"Output device config: \n  {yellow}{output_config}{reset}")
    sys.exit(0)

