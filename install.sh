#!/bin/bash
set -euo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

cp deadman.py /deadman.py
cp deadman.service /etc/systemd/system/deadman.service
cp mount_data.sh /path/to/mount_data.sh
cp unmount_data.sh /path/to/unmount_data.sh

# Adjust ownership & permissions (recommended)
chown root:root /deadman.py
chmod 700 /deadman.py

chown root:root /etc/systemd/system/deadman.service
chmod 644 /etc/systemd/system/deadman.service

chown root:root /path/to/mount_data.sh
chmod 700 /path/to/mount_data.sh

chown root:root /path/to/unmount_data.sh
chmod 700 /path/to/unmount_data.sh

systemctl daemon-reload
systemctl enable deadman
systemctl start deadman
