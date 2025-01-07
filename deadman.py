#!/usr/bin/python3

import logging
from subprocess import call, run, DEVNULL, PIPE, CalledProcessError, check_output
from re import compile, I
from time import sleep, strftime, localtime
from sys import exit
from datetime import datetime

################################################
# Configuration Variables
################################################

# Logging level: "INFO" by default, or "DEBUG" for detailed troubleshooting.
LOG_LEVEL = "INFO"  # INFO or "DEBUG"

# When True, prints "Would shutdown." When False, actually shuts down.
THIS_IS_A_TEST = False

# Hosts to ping. Typically you want things that are highly secure and always available. i.e. Google DNS and your home router.
host_list = ["8.8.8.8", "192.168.1.1"]

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

# Global constant for powering off the system (instead of hardcoding in immediate_poweroff()).
POWER_OFF_COMMAND = ["shutdown", "--poweroff", "now"]

################################################
# Set up Python logging
################################################

# Configure the logging level
logging.basicConfig(
    level=logging.DEBUG if LOG_LEVEL == "DEBUG" else logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

################################################
# Helper Functions
################################################

def run_command(cmd):
    """
    Runs a command. If LOG_LEVEL == "DEBUG", capture and log stdout/stderr in detail.
    Otherwise, discard output. Returns the command's exit code.
    """
    if LOG_LEVEL == "DEBUG":
        logger.debug(f"Running command (DEBUG mode): {' '.join(cmd)}")
        try:
            # capture_output=True is shorthand for stdout=PIPE, stderr=PIPE
            result = run(cmd, capture_output=True, text=True, check=False)
            logger.debug(f"Command return code: {result.returncode}")
            if result.stdout:
                logger.debug(f"Command stdout:\n{result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"Command stderr:\n{result.stderr.strip()}")
            return result.returncode
        except CalledProcessError as e:
            logger.debug(f"Command raised CalledProcessError: {e}")
            return e.returncode
        except Exception as ex:
            logger.debug(f"Command raised unexpected exception: {ex}")
            return 1  # Non-zero indicates failure
    else:
        # In non-DEBUG mode, discard output for brevity
        logger.debug(f"Running command (INFO mode): {' '.join(cmd)}")
        return call(cmd, stdout=DEVNULL, stderr=DEVNULL)

def return_datetime_string_now():
    epoc_utc_now = int(datetime.utcnow().timestamp())
    return strftime("%Y-%m-%d %H:%M:%S", localtime(epoc_utc_now))

def get_usb_devices():
    """
    Returns a list of dicts with USB device info from lsusb output.
    """
    device_re = compile(b"Bus\\s+(?P<bus>\\d+)\\s+Device\\s+(?P<device>\\d+).+ID\\s(?P<id>\\w+:\\w+)\\s(?P<tag>.+)$", I)
    
    # If debugging, capture lsusb output in detail
    if LOG_LEVEL == "DEBUG":
        logger.debug("Running lsusb for USB device list.")
        result = run(["lsusb"], capture_output=True, text=False, check=False)
        if result.returncode != 0:
            logger.debug(f"lsusb failed, return code = {result.returncode}")
            logger.debug(f"stderr:\n{result.stderr.decode('utf-8', errors='ignore') if result.stderr else ''}")
            return []
        df = result.stdout
        logger.debug(f"lsusb raw output:\n{df.decode('utf-8', errors='ignore')}")
    else:
        df = check_output(["lsusb"])

    devices = []
    for i in df.split(b'\n'):
        if i:
            info = device_re.match(i)
            if info:
                dinfo = info.groupdict()
                dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                devices.append(dinfo)

    if LOG_LEVEL == "DEBUG":
        logger.debug(f"Parsed USB devices:\n{devices}")
    return devices


def ping(host):
    """
    Returns True if ping succeeds, False otherwise.
    Logs debug output if LOG_LEVEL == "DEBUG".
    """
    command = ["timeout", wait_for_ping_seconds, "ping", "-c", "1", host]
    rc = run_command(command)
    return rc == 0

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
    Immediately forces system poweroff using the global POWER_OFF_COMMAND.
    """
    logger.info("Forcing immediate poweroff.")
    call(POWER_OFF_COMMAND)

################################################
# Shutdown / Failure Logic
################################################

def failure_action():
    """
    Called when conditions for shutdown are met.
    Iterates over shutdown_commands (which already include 'timeout', 'umount', etc.).
    If ANY command fails or times out, calls immediate_poweroff().
    """
    logger.info("Shutdown triggered.")

    if THIS_IS_A_TEST:
        # Only log the commands that would be executed
        for cmd in shutdown_commands:
            logger.info("Would execute: " + " ".join(cmd))
        logger.info("Would shutdown.")
        return

    # Actually run the commands
    for cmd in shutdown_commands:
        ret = run_command(cmd)
        if ret != 0:
            logger.error(f"Command '{' '.join(cmd)}' failed or timed out. Forcing poweroff now.")
            immediate_poweroff()
            return

    # If all commands succeeded, power off
    logger.info("All shutdown commands succeeded. Forcing poweroff now.")
    immediate_poweroff()

################################################
# Main Program
################################################

def main():
    logger.info("Dead Man's Shutdown is starting.")
    logger.info(f"Delaying for {startup_delay} seconds before beginning checks...")
    sleep(startup_delay)

    # Ensure all hosts can ping at startup
    for _ in range(failure_threshold):
        for host in host_list:
            if not ping(host):
                logger.warning("Network seems unavailable at startup. Dead Man's Shutdown will exit.")
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
            success = ping(host)
            if not success:
                host_failures[host] += 1
                if LOG_LEVEL == "DEBUG":
                    logger.debug(f"Ping to {host} failed. Current failure count = {host_failures[host]}")

        # Check if USB devices changed
        current_usb_devices = get_usb_devices()
        if current_usb_devices != original_usb_devices:
            logger.info("USB device list changed from original. Initiating shutdown.")
            failure_action()
            return

        # Check if any host reached the failure threshold
        for h, fcount in host_failures.items():
            if fcount >= failure_threshold:
                logger.info(f"Failed to ping {h} {failure_threshold} times within last {reset_failures_after_n_cycles} checks.")
                failure_action()
                return

        sleep(frequency)

if __name__ == "__main__":
    main()
