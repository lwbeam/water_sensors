# D-Link Wi-Fi Water Sensor (DCH-S160)

This Python script monitors one or more D-Link DCH-S160 Water Sensors and sends an e-mail and/or push notification whenever a change in status is detected. Specifically, a notification is sent when a sensor:
- detects the presents of water,
- no longer detects the presents of water,
- becomes disconnected from the network, or
- is reconnected to the network.

The script was developed on a Raspberry Pi 3B+ single board computer running Buster, but will likely run on any Linux-based computer, with little or no modification.  Push notifications were implemented using [Pushover](https://pushover.net). This feature requires the user to create their own Pushover account. 

## Background

The D-Link DCH-S160 Wi-Fi Water Sensor was introduced in late 2015. The sensor has no WebUI of its own, relying entirely on D-Link's cloud services and free **mydlink Home** mobile app for all of its functionality. Initially the app provided push notification and IFTTT support. E-mail support was eventually added, but was quietly disabled in 2020, even though the app _appears_ to still provide this feature. During 2019 D-Link withdrew all technical support for this product, and in early 2022 announced that it was withdrawing all support for the **mydlink Home** app. At the end of 2022 users will no longer be able to login into their D-Link accounts via this app, the app will be removed from the Apple and Android app stores, and it will cease to function. Furthermore, any devices not supported by D-Link's current mobile app will also become unusable. This includes the DCH-S160 Wi-Fi Water Sensor.

## Installation
#### 1. Copy Files
Place the Python script and associated `json` configuration files in the same folder (e.g., `sensors`). This can be done using the following commands:
```Shell
sudo apt install git
git clone https://github.com/lwbeam/water-sensors sensors
cd sensors
``` 
Ensure that the script is executable using the following command:
```Shell
chmod +x water_sensors.py
``` 
#### 2. Configure Router
If your Water Sensor is already connected to your network, to use this script the only thing you **must** do is ensure that your router is configured to assign a static IP address to the sensor. Refer to your router's user manual for instructions on how to accomplish this.

However, if you've aquired a _new_ Water Sensor, have replaced your router, or for whatever reason had to _reset_ an existing Water Sensor, you'll need to configure your router to provide the Water Sensor with access to your Wi-Fi network. In the past this would have been done entirely via the **mydlink Home** app. Without the app, it must be done using Wi-Fi Protected Setup Pushbutton Configuration (WPS-PBC). To accomplish this, complete the following steps:
- Ensure **Router's WPS-PBC** feature is enabled. Refer to your router's user manual for instructions on how to accomplish this. If your router doesn't have this feature, you'll need to find some other way to allow your sensor access to your Wi-Fi network.
- **Factory Reset** the Water Sensor. The reset button is located in the hole below the WPS button on the side of the sensor. Using a bent paperclip, hold down the reset button for at least 5 seconds, or until the LED on the side of the senser goes solid red. Release the button and wait until the red light on the **front** of the sensor goes out. The LED on the side should still be solid red.
- **Power Cycle** the Water Sensor. Unplug the senser, then plug it back in. Wait for light on the **front** of the sensor to go out and the LED on the side of the sensor to blink orange.
- Press and release the **Router's WPS Button**.
- Press and release the **Water Sensor's WPS Button**. The LED on the side of the sensor should start to blink green. Wait until it goes solid green.
- Configure your router to assign a **static IP address** to the Water Sensor.

#### 3. Configure Sensors
The `config.json` file contains an array of objects; one for each Water Sensor. Each object has five properties: `name`, `address`, `pin`,  `online`, and `status`. `online` and `status` are used by the script to keep track of whether or not the sensor is connected to the network or in the alarm state (i.e., has detected water).

To properly configure the script, ensure that there is an object in the `sensor` array for each Water Sensor connected to your network, and update the `name`, `address`, and `pin` for each. `name` is used to identify the Water Sensor in the e-mail and/or push notifications, `address` is its static IP address, and `pin` is its security PIN code (see the label on the back of your Water Sensor). In its present form, the file contains two objects. If you only have one Water Sensor, you must delete the unused object.

```json
{
    "sensor": [
        {
            "name": "Your name for this sensor or its location",
            "address": "XXX.XXX.XXX.XXX",
            "pin": "123456",
            "online": true,
            "status": false
        },
        {
            "name": "Your name for this sensor or its location",
            "address": "XXX.XXX.XXX.XXX",
            "pin": "123456",
            "online": true,
            "status": false
        }
    ]
}
```
#### 4. E-mail Notification (optional)
The `smtp.json` file contains a single object, with nine properties. To enable e-mail notifications, set `enabled` to `true`, and update the remaining properties with the correct information. `server` is the URL for your e-mail service provider's smtp server. `port` is the port used by the smtp server (usually 25 or 587). `userid` and `password` are your e-mail login credentials.  `name` is text displayed by some e-mail clients in lieu of the sender's e-mail address. `sender` and `recipient` are the sender's and recipient's e-mail addresses, respectively. `subject` is the text displayed on the subject line of each e-mail.

```json
{
    "enabled": false,
    "server": "smtp.example.com",
    "port": 587,
    "userid": "first.last@example.com",
    "password": "password",
    "name": "First Last",
    "sender": "first.last@example.com",
    "recipient": "first.last@example.com",
    "subject": "E-mail Subject Line"
}
```
#### 5. Push Notification (optional)
Push notifications were implemented using [Pushover](https://pushover.net). This feature requires the user to create their own Pushover account. When you create an account, you're assigned a unique _user key_. You'll also need to create a _token_ for this application. Pushover offers a free 30-day trial period, after which you're charged a small one-time fee to continue using their service. I have no affiliation with Pushover, and simply chose it because I was already using it for another application. 

The `push.json` file contains a single object, with five properties. To enable push notifications, set `enabled` to `true`, and update the remaining properties with the correct information. `token` is **Your API Token/Key**, generated by you for this application on the Pushover website. `user` is **Your User Key**, assigned when you created your Pushover account. `title` is the text displayed on the title line of each push notification. `sound` is the sound played when receiving a push notification (see Pushover documentation for options).
```json
{
    "enabled": false,
    "token": "Your API Token/Key",
    "user": "Your User Key",
    "title": "Push notification title",
    "sound": "pushover"
}
```
#### 6. Create Service
The Python script is designed to run as a `service`. To create the service, place definition file `water-sensor.service` in the `/etc/systemd/system` folder. In its present form, this file assumes that the script and associated configuration files were placed in the `/home/pi/sensors` folder. If this is not the case, `WorkingDirectory` (line 7) must be updated with their correct location. Start the service using the following commands:

```Shell
sudo chmod 644 /etc/systemd/system/water-sensor.service
sudo systemctl daemon-reload
sudo systemctl enable water-sensor.service
sudo systemctl start water-sensor.service
```

## Acknowledgements
I've spent many hours attempting to gain a basic understanding of SOAP and HNAP, and am no closer to being able to produce anything remotely useable. As a result, the Python classes (`NanoSOAPClient` and `HNAPClient`) used in this script, were shamelessly _borrowed_ from [Pierre Ståhl](https://github.com/postlund/dlink_hnap). I must also _confess_ that the class `WaterSensor` is based entirely on another of his Python classes, and that other bits of his code have found their way into my `Main` function. I am extremely grateful to him for sharing his code.
