import network
import time
import mrequests as requests
import gc
import machine
import prefs

DEBUG = 1

# Adapted from official ntptime by Peter Hinch July 2022
# The main aim is portability:
# Detects host device's epoch and returns time relative to that.
# Basic approach to local time: add offset in hours relative to UTC.
# Timeouts return a time of 0. These happen: caller should check for this.
# Replace socket timeout with select.poll as per docs:
# http://docs.micropython.org/en/latest/library/socket.html#socket.socket.settimeout

import socket
import struct
import select
from time import gmtime

# (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
# (date(1970, 1, 1) - date(1900, 1, 1)).days * 24*60*60
NTP_DELTA = 3155673600 if gmtime(0)[0] == 2000 else 2208988800

# The NTP host can be configured at runtime by doing: ntptime.host = 'myhost.org'
host = "pool.ntp.org"

def get_ntp_time(hrs_offset=0):  # Local time offset in hrs relative to UTC
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    try:
        addr = socket.getaddrinfo(host, 123)[0][-1]
    except OSError:
        return 0
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    poller = select.poll()
    poller.register(s, select.POLLIN)
    try:
        s.sendto(NTP_QUERY, addr)
        if poller.poll(1000):  # time in milliseconds
            msg = s.recv(48)
            val = struct.unpack("!I", msg[40:44])[0]  # Can return 0
            return max(val - NTP_DELTA + hrs_offset * 3600, 0)
    except OSError:
        pass  # LAN error
    finally:
        s.close()
    return 0  # Timeout or LAN error occurred


def set_time(timezoneOffset=0):
    """Sets real time clock using NTP, using the specified time zone offset.
    Args:
        timezoneOffset: hours to offset from UTC
    """
    currentTime = 0
    time_attempts = 1000
    while currentTime == 0:
        gc.collect()
        currentTime = get_ntp_time(timezoneOffset)
        time_attempts = time_attempts - 1
        if time_attempts == 0:
            break
        elif DEBUG > 1:
            print("set_time attempt", time_attempts, currentTime)
    if currentTime == 0:
        return
    tm = time.gmtime(currentTime)
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
    if DEBUG:
        print("set_time", tm)


def connect_wlan(ssid, password, resetap=True, deviceName="Dreamlight"):
    """Connects to the network.
    Args:
        ssid: Service name of Wi-Fi network.
        password: Password for that Wi-Fi network.
        resetap: Whether the access point should be deactivated.
    Returns:
        ip address off connected network
    """
    if resetap:
        ap_if = network.WLAN(network.AP_IF)
        ap_if.active(False)
        ap_if.disconnect()

    sta_if = network.WLAN(network.STA_IF)
    hostname = 'dl-' + deviceName.replace(' ', '-').lower()

    if not sta_if.isconnected():
        print("Connecting to WLAN ({})...".format(ssid))
        sta_if.config(hostname=hostname)
        sta_if.active(True)
        sta_if.connect(ssid, password)
        connection_attempts = 15
        while connection_attempts > 0:
            if sta_if.isconnected():
                break
            connection_attempts = connection_attempts - 1
            time.sleep_ms(500)
            pass

    if DEBUG:
        print("connected with ip", sta_if.ifconfig())

    return sta_if.ifconfig()[0]


def connect_ap(ssid, password, resetap=True, deviceName="Dreamlight"):
    """Configures WLAN interface as an access point, then scans wifi and returns list of available networks.
    Args:
        ssid: Name of access point
        password: Password for access point
    Returns:
        List of networks as tuples with 6 fields ssid, bssid, channel, RSSI, security, hidden
    """
    networks = []
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(False)
    sta_if.disconnect()
    ap = network.WLAN(network.AP_IF)
    hostname = 'dl-' + deviceName.replace(' ', '-').lower()
    ap.config(ssid=ssid, password=password, hostname=hostname)
    ap.active(True)
    print("Connect to WiFi: " + ssid + " / " + password + " and visit http://" + ap.ifconfig()[0] + " to continue setup...")
    gc.collect()
    return sta_if.scan()


# doesn't currently work
#from mdns_client import Client
#from mdns_client.responder import Responder
# async def setup_mdns():
#     local_ip = wlan.ifconfig()[0]
#     print(f"Setting up MDNS on local ip: {local_ip}")
#     client = Client(local_ip)
#     host = "bedlight.local"
#     responder = Responder(
#         client,
#         own_ip=lambda: local_ip,
#         host=lambda: host,
#     )
#     responder.debug = True
#     responder.advertise("web", "_tcp", port=80)

def getCommitHash(url, headers):
    """ Gets the commit hash for a raw Github URL.
    Args:
        url: URL to find commit hash for, e.g. 'https://raw.githubusercontent.com/mcarlson/iotkit/main'
        headers: HTTP headers, including Authorization if needed.
    Returns:
        Git commit hash
    """
    org, repo, branch = url.replace('https://raw.githubusercontent.com/', '').split('/')
    commitHashURL = 'https://api.github.com/repos/%s/%s/commits/%s' % (org, repo, branch)
    commits = getJSON(commitHashURL, headers=headers)
    if commits and 'sha' in commits:
        return commits['sha']


def checkForUpdates(url="https://raw.githubusercontent.com/...", token="0xdeadbeef", files=["main.py"], cleanup=[]):
    """ Checks for updates by comparing the hash of each file against a published version
    Args:
        url: Base URL to load from
        files: List of filenames to check
        cleanup: List of files to delete after update
        token: HTTP Authorization token
    Returns:
        Array of networks
    """
    headers = {'User-Agent': 'request', 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = 'Bearer %s' % token,

    commithash = getCommitHash(url, headers)
    if commithash and commithash != prefs.get('commithash', ''):
        gc.collect()
        print("Getting updates for commit", commithash, 'free memory', gc.mem_free())
        import senko
        OTA = senko.Senko(url=url, files=files, headers=headers, debug=DEBUG, cleanup=cleanup)
        if OTA.update():
            print("Updated to the latest version. Rebooting...")
            prefs.set('commithash', commithash)
            time.sleep(1)
            machine.reset()
        prefs.set('commithash', commithash)
        del(OTA)
        del(senko)
    else:
        print("Commit hash unchanged, skipping updates.")
    gc.collect()
        
            
def getJSON(*args, **kwargs):
    """ Loads JSON from the specified url
    Args:
        url: URL to load JSON from
    Returns:
        JSON object
    """
    gc.collect()
    response = requests.get(*args, **kwargs)
    if DEBUG:
        print('getJSON: ', args, kwargs)
    if response.status_code == 200:
        json = response.json()
        if DEBUG:
            print('getJSON result: ', json)
        return json


def postJSON(*args, **kwargs):
    """ POSTs JSON to the specified url
    Args:
        url: URL to load JSON from
    Returns:
        JSON object
    """
    gc.collect()
    response = requests.post(*args, **kwargs)
    if DEBUG:
        print('postJSON: ', args, kwargs)
    if response.status_code == 200:
        json = response.json()
        if DEBUG:
            print('getJSON result: ', json)
        return json


def getTimeZoneOffset():
    """ Gets the time zone offset via GEOIP
    Args:
    Returns:
        timezone offset in hours
    """
    locationData = getJSON('https://get.geojs.io/v1/ip/geo.json')
    if DEBUG:
        print(locationData)
    timezoneData = getJSON('https://worldtimeapi.org/api/timezone/' + locationData['timezone'])
    if DEBUG:
        print(timezoneData)
    tzOffset = int((int(timezoneData['raw_offset']) + int(timezoneData['dst_offset'])) / 3600)
    return tzOffset