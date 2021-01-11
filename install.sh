#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi


cp dead_mans_shutdown.py /dead_mans_shutdown.py
cp deadman.service /etc/systemd/system/deadman.service

systemctl daemon-reload
systemctl enable deadman
systemctl start deadman

