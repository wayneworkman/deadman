# Dead Man's Shutdown

This is a utility to secure a Linux system via shutdown. For this utility to provide security, the system being shutdown must have everything on its disk encrypted (except for the `/boot` partition) and upon booting a password must be required for decryption. Any swap partitions must also be encrypted, or non-existant.

Shutdown is activated in the following scenarios.

* If a list of hosts fail ping commands for a designated number of times, shutdown.
* If the USB device list changes after this utility has started, shutdown.

If the list of hosts fail to ping at all during 3 consecutive attempts when this utility first starts, the script exits. Because for this script to run at all, the rightful system owner must have already decrypted the disk, and we don't want to lock out the rightful owner if there's some network issue going on.

# Installation

Run `install.sh` as root. This will:

* copy the python script to `/deadman.py`
* copy the systemd file to `/etc/systemd/system/deadman.service`
* Reload systemd services
* enable a new service called `deadman`
* start the new service called `deadman`

# Starting, Stopping, Enabling, Disabling, status

To enable on boot: `systemctl enable deadman`

To disable on boot: `systemctl disable deadman`

To start: `systemctl start deadman`

To stop: `systemctl stop deadman`

To restart: `systemctl restart deadman`

Get Status: `systemctl status deadman -l`


# Configuration

All configuration exists within the python script `deadman.py` towards the top of the script. The installed location is `/deadman.py` so you would need to edit it there after installation. Each variable has comments describing what it does. If you change the configuration when the utility is already running, you need to either restart the service or reboot.



