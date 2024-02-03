from machine import Pin, Timer
import gc
import netutil
import prefs
import time

DEBUG = prefs.get('DEBUG', 0)
prefs.set('VERSION', '1.0.0')
VERSION = prefs.get('VERSION', '1.0.0')

led = Pin("LED", Pin.OUT)
led.on()

import os
def file_exists(filename):
    try:
        #print("File exists", filename,(os.stat(filename)[0] & 0x4000) == 0)
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError as e:
        #print("Error: %s", e, filename)
        return False

def checkForUpdates():
    gc.collect()
    netutil.checkForUpdates(
        prefs.get('update_url', 'https://raw.githubusercontent.com/mcarlson/iotkit/main'),
        files=["main.py", "netutil.py", "prefs.py", "mrequests.py", "senko.py", "microdot.py", "index.html", "setup.html", "static/bootstrap.min.css.gz"],
        cleanup=[],
        token=prefs.get('auth_token', ''),
    )

# a list of available wifi hotspots, empty until connectAP() is called
networks = []
def connectAP():
    global networks
    networks = netutil.connect_ap('dreamlight', 'dreamlight', deviceName=prefs.get('deviceName', 'dreamlight'))


ip = ""
connected = ""
if prefs.get('ssid', 'SETME') == 'SETME' or prefs.get('password', 'SETME') == 'SETME':
    connectAP()
else:
    ip = netutil.connect_wlan(prefs.get('ssid', 'SETME'), prefs.get('password', 'SETME'), deviceName=prefs.get('deviceName', 'iotkit'))
    if not ip or ip == '0.0.0.0':
        reboots = prefs.set('reboots', prefs.get('reboots', 3) - 1)
        print("Wifi connection failed.", reboots, 'reboot attempts remaining.')
        if reboots > 0:
            time.sleep(2)
            machine.reset()
        connectAP()
        if DEBUG:
            print("Found networks", networks)
    else:
        prefs.set('reboots', 3)
        connected = ip
        netutil.set_time(int(prefs.get('timezoneOffset', 2)))
        if not DEBUG:
            checkForUpdates()

led.off()

# web server
import uasyncio as asyncio
import json
import sys

from microdot import Microdot, send_file

app = Microdot()

@app.get('/')
async def index(request):
    if len(networks):
        return send_file('/setup.html', max_age=3600)
    else:
        return send_file('/index.html', max_age=3600)

@app.get('/setup')
async def index(request):
    return send_file('/setup.html', max_age=3600)

@app.route('/static/<path:path>')
async def static(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    filepath = 'static/' + path
    if file_exists(filepath + '.gz'):
        return send_file(filepath, max_age=86400, compressed=True, file_extension='.gz')
    else:
        return send_file(filepath, max_age=86400)

@app.get('/prefs')
async def getPrefs(request):
    return json.dumps(prefs.getAll())

@app.post('/prefs')
async def setPrefs(request):
    newprefs = request.json
    prefs.setAll(newprefs)
    return json.dumps(newprefs)

@app.get('/wifi/networks')
async def scanWifi(request):
    return json.dumps(networks)

@app.post('/wifi')
async def testWifi(request):
    global connected
    creds = request.json
    ip = netutil.connect_wlan(creds['ssid'], creds['password'], resetap=False, deviceName=prefs.get('deviceName', 'iotkit'))
    connectAP()
    if ip and ip != '0.0.0.0':
        connected = ip
        prefs.setAll(creds)
        if DEBUG:
            print('Wifi connection successful!')
        return ip
    if DEBUG:
        print("Invalid wifi password.")
    return "password"

@app.post('/restart')
async def restart(request):
    machine.reset()


def startServer(debug):
    try:
        gc.collect()
        await app.start_server(port=80, debug=debug)
    except Exception as e:
        print("server exception", e)
        startServer()

def runProgram():
    # called to set up your program before the web server starts, e.g. to set up Timers, etc.
    pass

async def main():
    if connected:
        try:
            await runProgram()
            print('Configure at http://' + connected)
        except Exception as e:
            sys.print_exception(e)
            print('top-level exception, forcing DEBUG to 0 and checking for updates.', e)
            prefs.set('DEBUG', 0)
            checkForUpdates()
    else:
        # Start flashing LED for setup
        blinktimer = Timer(period=500, callback=lambda t:led.toggle())
    
    while True:
        task = asyncio.create_task(startServer(DEBUG))
        await task
        await asyncio.sleep(1)

asyncio.run(main())