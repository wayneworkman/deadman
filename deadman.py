#!/usr/bin/python3

from subprocess import call, DEVNULL, check_output
from re import compile, I
from time import sleep, strftime, localtime
from sys import exit
from datetime import datetime

################################################
# Configuration Variables
################################################

# When True, prints "Would shutdown." When False, actually shuts down.
THIS_IS_A_TEST = False

# Hosts to ping.
host_list = ["8.8.8.8", "10.0.0.1"]

# Frequency (in seconds) to check ping and USB devices
frequency = 2

# Number of consecutive ping failures for any host before initiating shutdown
failure_threshold = 10

# Number of cycles before resetting ping failure counts
reset_failures_after_n_cycles = 15

# Time to wait for the ping command to return (string, seconds)
wait_for_ping_seconds = "4"

# Startup delay in seconds before capturing initial USB device list and starting ping checks
startup_delay = 60

# A single, user-editable list of commands for shutdown.
#  - Each item is a list of strings: the command plus args.
#  - If any fail or time out, we do an immediate forced poweroff.
shutdown_commands = [
    ["timeout", "1", "umount", "-f", "/data"],
    ["timeout", "1", "cryptsetup", "close", "encrypted"]
]

################################################
# Helper Functions
################################################

def return_datetime_string_now():
    epoc_utc_now = int(datetime.utcnow().timestamp())
    return strftime("%Y-%m-%d %H:%M:%S", localtime(epoc_utc_now))

def log(line):
    """
    Logs to stdout, which systemd/journald captures.
    """
    line = return_datetime_string_now() + " " + line
    print(line, flush=True)

def get_usb_devices():
    """
    Returns a list of dicts with USB device info from lsusb output.
    """
    device_re = compile(b"Bus\\s+(?P<bus>\\d+)\\s+Device\\s+(?P<device>\\d+).+ID\\s(?P<id>\\w+:\\w+)\\s(?P<tag>.+)$", I)
    df = check_output(["lsusb"])
    devices = []
    for i in df.split(b'\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                devices.append(dinfo)
    return devices

def ping(host):
    """
    Returns True if ping succeeds, False otherwise.
    """
    command = ["timeout", wait_for_ping_seconds, "ping", "-c", "1", host]
    return call(command, stdout=DEVNULL, stderr=DEVNULL) == 0

def reset_host_failures():
    """
    Initialize or reset the host_failures dictionary to zero for each host.
    """
    hf = {}
    for h in host_list:
        hf[h] = 0
    return hf

def immediate_poweroff():
    """
    Immediately forces system poweroff.
    """
    call(["poweroff", "-f"])

################################################
# Shutdown / Failure Logic
################################################

def failure_action():
    """
    Called when conditions for shutdown are met.
    Iterates over shutdown_commands (which already include 'timeout', 'umount', etc.).
    If ANY command fails or times out, calls immediate_poweroff().
    """
    log("Shutdown triggered.")

    if THIS_IS_A_TEST:
        # Only log the commands that would be executed
        for cmd in shutdown_commands:
            log("Would execute: " + " ".join(cmd))
        log("Would shutdown.")
        return

    # Actually run the commands
    for cmd in shutdown_commands:
        ret = call(cmd, stdout=DEVNULL, stderr=DEVNULL)
        if ret != 0:
            log(f"Command '{' '.join(cmd)}' failed or timed out. Forcing poweroff now.")
            immediate_poweroff()
            return

    # If all commands succeeded, power off
    log("All shutdown commands succeeded. Forcing poweroff now.")
    immediate_poweroff()

################################################
# Main Program
################################################

def main():
    log("Dead Man's Shutdown is starting.")
    log(f"Delaying for {startup_delay} seconds before beginning checks...")
    sleep(startup_delay)

    # Ensure all hosts can ping at startup
    for _ in range(failure_threshold):
        for host in host_list:
            if not ping(host):
                log("Network seems unavailable at startup. Dead Man's Shutdown will exit.")
                exit(1)

    # Capture the original USB device list
    original_usb_devices = get_usb_devices()

    # Initialize host failure counters
    host_failures = reset_host_failures()
    count = 0

    # Main loop
    while True:
        if count >= reset_failures_after_n_cycles:
            host_failures = reset_host_failures()
            count = 0

        count += 1

        # Check pings
        for host in host_list:
            if not ping(host):
                host_failures[host] += 1

        # Check if USB devices changed
        current_usb_devices = get_usb_devices()
        if current_usb_devices != original_usb_devices:
            log("USB device list changed from original. Initiating shutdown.")
            failure_action()
            return

        # Check if any host reached the failure threshold
        for h, fcount in host_failures.items():
            if fcount >= failure_threshold:
                log(f"Failed to ping {h} {failure_threshold} times within last {reset_failures_after_n_cycles} checks.")
                failure_action()
                return

        sleep(frequency)

if __name__ == "__main__":
    main()
