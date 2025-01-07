# Dead Man's Shutdown

This is a utility to secure a Linux system by forcing a shutdown under certain conditions. The system must be fully encrypted (except for ```/boot```) so that on boot, a decryption password (or temporarily inserted hardware token) is required. Swap should also be encrypted or non-existent.

## Shutdown Triggers

* If any one of a configured list of hosts fails ping commands for a certain number of times, the system shuts down.
* If the USB device list changes from the time this script starts, the system shuts down.

When this utility starts, it does a quick check to ensure that all listed hosts can be pinged. If they can't, it exits (rather than shutting down). This is to avoid locking out the rightful owner if there's a legitimate network issue right at startup.

## Startup Delay

When the service is started, there is a default delay (configurable in the ```deadman.py```) that allows you to remove, for example, a keyboard used for decryption before the service captures the “original” USB device list.

## Installation

Run ```install.sh``` as root. This will:
* Copy the python script to ```/deadman.py```
* Copy the systemd file to ```/etc/systemd/system/deadman.service```
* Reload systemd
* Enable the ```deadman``` service
* Start the ```deadman``` service
* Copy mount & unmount utility scripts to root's home directory.
  * These scripts are not used by the main logic. They are present to ease manual mounting & unmounting of encrypted volumes.

## Service Control

* Enable on boot: ```systemctl enable deadman```
* Disable on boot: ```systemctl disable deadman```
* Start: ```systemctl start deadman```
* Stop: ```systemctl stop deadman```
* Restart: ```systemctl restart deadman```
* Status: ```systemctl status deadman -l```

## Configuration

All configuration lives near the top of ```deadman.py```. After installation, edit ```/deadman.py``` accordingly, then restart the service or reboot to apply changes.

## Security Hardening & Checksums

This project includes the following security enhancements:

1. **Systemd Hardening**:  
   - Certain directories are mounted read-only, home directories are protected, and the service has a restricted set of capabilities.  
   - See ```deadman.service``` for details.

2. **Forced Unmount with 1-Second Grace**:  
   - When shutdown conditions are met, this script tries to unmount ```/data``` for up to 1 second.  
   - If unmount still hangs (e.g., due to open files), the system proceeds with immediate power-off.
   - These commands are configurable within the global constant ```shutdown_commands```.

3. **Global Power-Off Command**:  
   - The final forced power-off uses a global constant ```POWER_OFF_COMMAND```.  
   - You can change this if you prefer a different shutdown tool (for example, ```poweroff``` instead of ```shutdown```).

4. **Stricter Shell Scripts**:
   - Scripts now use ```set -euo pipefail``` and absolute paths, reducing the risk of unexpected behaviors or PATH hijacking.

## Logging

The Python script logs directly to stdout/stderr. Systemd/journald captures this output, which you can view with ```journalctl -u deadman``` or ```systemctl status deadman```.

## Usage

Once installed and running, normal usage does not change. However, be aware that an unexpected change in USB devices or repeated ping failures will cause an **immediate** shutdown. Ensure your network is stable and that you unplug any devices you don’t need within the startup delay window.
