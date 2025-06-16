#!/bin/bash

set -euxo pipefail

#find ui/tests/ -maxdepth 1 -name '*.pyc' -delete

#test -d ui/tests/__pycache__ && rm -rf ui/tests/__pycache__
test -d tests/__pycache__ && rm -rf tests/__pycache__
test -d .pytest_cache && rm -rf .pytest_cache/

sh test_commandline
