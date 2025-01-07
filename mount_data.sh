#!/bin/bash
set -euo pipefail
PATH=/usr/sbin:/usr/bin:/sbin:/bin

# Unmount /data just in case it's mounted; ignore errors
umount /data > /dev/null 2>&1 || true
# Optionally:
# umount -f /data 


# Open the encrypted partition
cryptsetup --type luks open /dev/sda3 encrypted

# Mount it
mount -t ext4 /dev/mapper/encrypted /data
