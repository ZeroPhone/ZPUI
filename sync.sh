#!/bin/bash

set -euo pipefail

TMP_DIR="/tmp/zpui_update"
INSTALL_DIR="/opt/zpui"

cd "$(dirname "$0")"  # Make sure we are in the script's directory when running
set -e  # Strict mode : script stops if any command fails

if test "$EUID" -ne 0
then
   echo "This script must be run as root, exiting..."
   exit 1
fi

mkdir -p "${INSTALL_DIR}"

# syncing config files before sync, so that they don't get overwritten!
rsync -av --include="*/" --include="*.yaml" --include "*.json" --exclude="*" "${INSTALL_DIR}"/ .

rsync -av --delete ./ --exclude='*.pyc' "${INSTALL_DIR}"
systemctl restart zpui.service
#rm -rf ${TMP_DIR}

echo "WARNING"
echo "If you have updated the system-wide ZPUI copy using Settings=>Update ZPUI,"
echo "it will no longer have those changes. No worries, though,"
echo "run `git pull` now and then run `./sync.sh` again."
exit 0
