#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi


cp deadman.py /deadman.py
cp deadman.service /etc/systemd/system/deadman.service

systemctl daemon-reload
systemctl enable deadman
systemctl start deadman

