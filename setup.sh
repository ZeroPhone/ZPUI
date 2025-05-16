#!/bin/bash

set -euo pipefail

INSTALL_DIR="/opt/zpui"

if test "$EUID" -ne 0
then
   echo "This script must be run as root, exiting..."
   exit 1
fi

[ -f config.yaml ] || cp default_config.yaml config.yaml
apt-get install python3 python3-pip python3-smbus python3-dev python3-pygame libjpeg-dev python3-serial nmap python3-gi
pip3 install --break-system-packages -r requirements.txt
mkdir -p ${INSTALL_DIR}
cp ./. ${INSTALL_DIR} -R
cd ${INSTALL_DIR}
cp zpui.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable zpui.service
#systemctl start zpui.service
