#!/bin/bash
set -euo pipefail
PATH=/usr/sbin:/usr/bin:/sbin:/bin

umount /data

# Or optionally:
# unmount -f /data

cryptsetup close encrypted
