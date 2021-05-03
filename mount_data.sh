#!/bin/bash
unmount /data > /dev/null 2>&1
cryptsetup --type luks open /dev/sda3 encrypted
mount -t ext4 /dev/mapper/encrypted /data
