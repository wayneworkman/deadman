#!/usr/bin/python3

# When True, prints "Would shutdown." When False, actually shuts down.
THIS_IS_A_TEST = False

# Hosts to ping.
host_list = ["www.google.com", "8.8.8.8", "mega.nz", "10.0.0.1"]

# Frequency to ping, in seconds
frequency = 3

# Number of ping failures for any of the hosts which would initiate shutdown.
failure_threshold = 3

# Number of cycles before resetting ping failure count.
reset_failures_after_n_cycles = 15



from subprocess import call, DEVNULL, check_output
from re import compile, I
from time import sleep

def get_usb_devices():
    device_re = compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", I)
    df = check_output("lsusb")
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
    command = ['timeout', '2', 'ping', '-c', '1', host]
    return call(command, stdout=DEVNULL, stderr=DEVNULL) == 0

def reset_host_failures():
    host_failures = {}
    for host in host_list:
        host_failures[host] = 0
    return host_failures

def failure_action():
    if THIS_IS_A_TEST:
        print("Would shutdown.")
    else:
        command = ['shutdown', 'now']
        call(command)

original_usb_devices = get_usb_devices()
host_failures = reset_host_failures()
count = 0
while True:
    if count >=  reset_failures_after_n_cycles:
        host_failures = reset_host_failures()
        count = 0
    count = count + 1
    for host in host_list:
        result = ping(host)
        if result is False:
            host_failures[host] = host_failures[host] + 1
    current_usb_devices = get_usb_devices()
    if current_usb_devices != original_usb_devices:
        failure_action()
    for key in host_failures.keys():
        if host_failures[key] >= failure_threshold:
            failure_action()
            count = 0
    sleep(frequency)
 

