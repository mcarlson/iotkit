# Micropython IOT kit

Micropython doesn't come with way to easily configure or manage your devices. This package provides a and easy 'out of the box' web-based UI for setup and configuration with a first-class user experience and no need to external displays or other hardware.

In order to connect to the local network, users need to provide the proper credentials. Initially the device's LED will be flashing, meaning means it's provided an access point/Wifi network for you to connect to. Once connected, you can visit the device's web server to finish the setup and configuration. See the Configuration section below for QR codes to ease this process.

Once a connection is established, the device can update its local time and optionally check for and apply software updates for your project/

To do all this, we've combined:
+ a simple and lightweight preferences system for persisting data between reboots
+ the awesome microdot webserver framework
+ an NTP (Network Time Protocol) implementation for accurately syncing the device's clock, with utilities for retrieving the correct timezone based on GeoIP
+ an OTA updater system that pulls updates from Github to keep your devices up-to-date (based on  Senko with a ton of improvements for low memory)
+ mrequests, a vastly improved replacement for micropython's requests library that supports chunked encoding for low memory use
+ all battle-tested so you don't have to worry about it


## Hardware setup:
1. Flash device with the lastest micropython version.
2. Copy all files to the root of the device

## Configuration:
1. Power on your device
2. Once the LED is flashing, connect to the setup accesspoint:
![setup website qr code](static/accesspoint_qrcode.png?raw=true])
3. Connect to the setup website and follow the instructions: ![setup website qr code](static/setup_qrcode.png?raw=true)
4. Enjoy your device

## Modification:
1. You can edit index.html and setup.html as you like. Be sure to add any necessary files for your project to the
