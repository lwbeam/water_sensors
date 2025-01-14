# D-Link Wi-Fi Water Sensor (DCH-S160)

This Python 3 script monitors one or more D-Link DCH-S160 Water Sensors and sends an e-mail and/or push notification whenever a change in status is detected. Specifically, a notification is sent when a sensor:
- detects the presents of water,
- no longer detects the presents of water,
- becomes disconnected from the network, or
- is reconnected to the network.

The script was developed on a Raspberry Pi 3B+ single board computer running Buster, but will likely run on any Linux-based computer, with little or no modification. Push notifications were implemented using [Pushover](https://pushover.net). This feature requires the user to create their own Pushover account.

The script also includes rudimentary [IFTTT](https://ifttt.com) support, which can be used to generate the above notifications via the **IFTTT** mobile app. It is hoped that this will provide the user with a starting point from which to create more complicated and useful IFTTT applets.

## Background

The D-Link DCH-S160 Wi-Fi Water Sensor was introduced in late 2015. The sensor has no WebUI of its own, relying entirely on D-Link's cloud services and free **mydlink Home** mobile app for all of its functionality. Initially the app provided push notification and IFTTT support. E-mail support was eventually added, but then quietly disabled in 2020, even though the app _appeared_ to still provide this feature. During 2019 D-Link withdrew all technical support for this product, and in early 2022 [announced](https://www.mydlink.com/faq#id-topFAQ/ans-4242) that it was withdrawing all support for the **mydlink Home** app. At the end of 2022 users were no longer able to login into their D-Link accounts via this app, the app was removed from the Apple and Android app stores, and it ceased to function. As a result, any device **not supported** by D-Link's current mobile apps has become unusable. This includes the DCH-S160 Wi-Fi Water Sensor.

## Installation
#### 1. Copy Files
Place the Python script and associated `json` configuration files in the same folder (e.g., `sensors`). This can be done using the following commands:
```Shell
sudo apt install git
git clone https://github.com/lwbeam/water_sensors sensors
cd sensors
``` 
Install dependent Python packages using the following commands:
```Shell
sudo apt install python3-pip
sudo pip3 install aiohttp xmltodict
```
Ensure that the script is executable using the following command:
```Shell
chmod +x water_sensors.py
``` 
#### 2. Configure Router
If your Water Sensor is already connected to your network, the only thing you **must** do to use this script is ensure that your router is configured to assign a static IP address to the sensor. Refer to your router's user manual for instructions on how to accomplish this.

However, if you've aquired a _new_ Water Sensor, replaced your router, or for whatever reason had to _reset_ an existing Water Sensor, you'll need to configure your router to provide the Water Sensor with access to your Wi-Fi network. In the past this would have been done entirely via the **mydlink Home** app. Without the app, it must be done using Wi-Fi Protected Setup Push-Button Configuration (WPS-PBC). To accomplish this, complete the following steps:
- Ensure **Router's WPS-PBC** feature is enabled. Refer to your router's user manual for instructions on how to accomplish this. If your router doesn't have this feature, you won't be able to connect your Water Sensor to your Wi-Fi network.
- **Factory Reset** the Water Sensor. The reset button is located in the hole below the WPS button on the side of the sensor. With the sensor plugged in, use a bent paperclip to hold in the reset button for at least 5 seconds, or until the LED on the side of the senser goes solid red. Release the button and wait until the red light on the **front** of the sensor goes out. The LED on the side should still be solid red.
- **Power Cycle** the Water Sensor. Unplug the senser, then plug it back in. Wait for the light on the **front** of the sensor to go out and the LED on the side of the sensor to blink orange.
- Press and release the **Router's WPS Button**.
- Press and release the **Water Sensor's WPS Button**. The LED on the side of the sensor should start to blink green. Wait until it goes solid green.
- Configure your router to assign a **static IP address** to the Water Sensor.

#### 3. Configure Sensors
The `config.json` file contains an array of objects; one for each Water Sensor. Each object has six properties: `enabled`, `name`, `address`, `pin`,  `online`, and `status`. `online` and `status` are used by the script to keep track of whether or not the sensor is connected to the network (`3`, `2` or `1` = _online_; `0` = _offline_) or in the alarm state (`true` = _water detected_; `false` = _water not detected_). Note that `online` actually tracks the remaining number of consecutive times a sensor is allowed to **not** respond to a _ping_ before it is considered _offline_. This was altered (from simply `true` or `false`) in an attempt to reduce the number of nuisance notifications due to intermittent Wi-Fi interference (e.g., microwave ovens), and can be adjusted by changing the value assigned to `failed_pings` on line 246 of `water_sensors.py`. 

To properly configure the script, ensure that there is an object in the `sensor` array for each Water Sensor connected to your network, and update the `enabled`, `name`, `address`, and `pin` properties for each. `enabled` can be used to _ignore_ a sensor (i.e., disable monitoring it) without having to remove its information from the file. `name` is used to identify the sensor in the e-mail and/or push notifications, `address` is its static IP address, and `pin` is its security PIN code (see the label on the back of the sensor). In its present form, the file contains two objects. If you only have one Water Sensor, you can either delete the unused object or leave its `enabled` property set to `false`.

```json
{
    "sensor": [
        {
            "enabled": true,
            "name": "Your name for this sensor or its location",
            "address": "XXX.XXX.XXX.XXX",
            "pin": "123456",
            "online": 3,
            "status": false
        },
        {
            "enabled": false,
            "name": "Your name for this sensor or its location",
            "address": "XXX.XXX.XXX.XXX",
            "pin": "123456",
            "online": 3,
            "status": false
        }
    ]
}
```
#### 4. E-mail Notification (optional)
The `smtp.json` file contains a single object with nine properties. To enable e-mail notifications, set `enabled` to `true`, and update the remaining properties with the correct information. `server` is the URL for your e-mail service provider's smtp server. `port` is the port used by the smtp server (usually 25 or 587). `userid` and `password` are your e-mail login credentials.  `name` is text displayed by some e-mail clients in lieu of the sender's e-mail address. `sender` and `recipient` are the sender's and recipient's e-mail addresses, respectively. `subject` is the text displayed on the subject line of each e-mail.

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
Whenever possible, the script bundles e-mail notifications together and sends them as a single message.
#### 5. Push Notification (optional)
Push notifications were implemented using [Pushover](https://pushover.net). This feature requires the user to create their own Pushover account, and install the Pushover mobile app. When you create an account, you're assigned a unique _user key_. You'll also need to create a _token_ for this application. Pushover offers a free 30-day trial period, after which you're charged a small one-time fee to continue using their service. I have no affiliation with Pushover, and simply chose it because I was already using it for another application.

The `push.json` file contains a single object with five properties. To enable push notifications, set `enabled` to `true`, and update the remaining properties with the correct information. `token` is **Your API Token/Key**, generated by you for this application on the Pushover website. `user` is **Your User Key**, assigned when you created your Pushover account. `title` is the text displayed on the title line of each push notification. `sound` is the sound played when receiving a push notification (see Pushover documentation for options).
```json
{
    "enabled": false,
    "token": "Your API Token/Key",
    "user": "Your User Key",
    "title": "Push notification title",
    "sound": "pushover"
}
```
Note that there are length limits associated with push notifications. Messages sent to **Android** devices have a title limit of 65 characters and a description limit of 240 characters. However, **iOS** devices have a combined limit of only 178 characters (about four lines of text). These limits should be taken into consideration when assigning a sensor's `name` and the push notification `title`. To ensure these limits are not exceeded, the script sends each push notification separately.
#### 6. IFTTT Support (optional)
This feature requires the user to create their own [IFTTT](https://ifttt.com) account and applet, and install the **IFTTT** mobile app. IFTTT offers a _free_ plan, as well as two paid [plans](https://ifttt.com/plans). Although the free plan provides limited features and functionality, and currently only allows the user to create two applets, it is sufficient to create the required applet. I have no affiliation with IFTTT, and simply chose it as D-Link had provided support for it. Although IFTTT was the first service of its kind, there are now several similar services available.

To create your IFTTT applet, log into your IFTTT account and click on `Create`. To configure the **If This** portion of your applet, click on `Add`, select the `Webhooks` service, and click on `Receive a web request`. Now enter your `Event Name` (e.g., water_sensor), and click on `Create trigger`. To configure the **Then That** portion of your applet, click on `Add`, select the `Notifications` service, and click on `Send a rich notification from the IFTTT app`. Erase the contents of the `Message` field and add _ingredient_ `Value2`. Erase the contents of the `Title` field and add _ingredient_ `Value1`. Leave the remaining two fields empty, and click on `Create action`. Finally, click on `Continue`, and then `Finish`.

The `ifttt.json` file contains a single object with six properties. To enable notifications via IFTTT, set `enabled` to `true`, and update the next three properties with the correct information. `key` is the **Webhooks Key**, generated when you created your IFTTT account. To find it, go [here](https://ifttt.com/maker_webhooks) while logged into your IFTTT acount, and click on `Documentation`. `event` is the **Event Name** that you assigned to the  _Webhooks trigger_ (e.g., water_sensor) when you created your applet. Finally, `value1` is the text displayed on the title line of each IFTTT notification. Leave `value2` and `value3` unchanged, as they have been included in this file to assist the user in customizing the script. Note that the script currently uses `value2` to send the generated message line of the notification to the IFTTT applet. Although, the script also sends the contents of `value3` to the applet, the applet currently does not use it.
```json
{
    "enabled": false,
    "key": "Webhooks Key",
    "event": "Event Name",
    "value1": "IFTTT notification title",
    "value2": "not used",
    "value3": "not used"
}
```
#### 7. Create Service
The Python script is designed to run as a `service`. To create the service, place definition file `water-sensor.service` in the `/etc/systemd/system` folder. In its present form, this file assumes that the script and associated configuration files were placed in the `/home/pi/sensors` folder. If this is not the case, `WorkingDirectory` (line 8) must be updated with their correct location. Start the service using the following commands:

```Shell
sudo chmod 644 /etc/systemd/system/water-sensor.service
sudo systemctl daemon-reload
sudo systemctl enable water-sensor.service
sudo systemctl start water-sensor.service
```
## Acknowledgements
I've spent many hours attempting to gain a basic understanding of SOAP and HNAP, and am no closer to being able to produce anything remotely useable. As a result, the Python classes (`NanoSOAPClient` and `HNAPClient`) used in this script, were shamelessly _borrowed_ from [Pierre Ståhl](https://github.com/postlund/dlink_hnap). I must also _confess_ that the class `WaterSensor` is based entirely on another of his Python classes, and that other bits of his code have found their way into my `Main` function. I am extremely grateful that he has shared his code.
