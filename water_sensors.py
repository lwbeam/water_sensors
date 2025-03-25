#!/usr/bin/env python3

# Monitor D-Link Water Sensor status.

import hmac
import logging
import asyncio
import aiohttp
import xmltodict
import xml.etree.ElementTree as ET

from io import BytesIO
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

def _hmac(key, message):
    return (hmac.new(key.encode("utf-8"), message.encode("utf-8"), digestmod="MD5").hexdigest().upper())


class AuthenticationError(Exception):

    """ Thrown when exception encountered. """

    def __init__(self, message):
        self.message = message
        _LOGGER.error("Authentication Error: %s", self.message)


class HNAPClient:

    """ Handles device login and HNAP request formatting, and returns response. """

    ACTION_URL = "http://purenetworks.com/HNAP1/"
    ACTION_NS = {"xmlns": ACTION_URL}
    BASE_NS = {
               "xmlns:soap": "http://schemas.xmlsoap.org/soap/envelope/",
               "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
               "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
              }


    def __init__(self, address, username, password, loop=None, session=None):

        self.address = address
        self.username = username
        self.password = password
        self.loop = loop
        self.session = session
        self.private_key = None
        self.auth_token = None
        self.cookie = None
        self.headers = {}


    def _generate_request_xml(self, method, **kwargs):

        body = ET.Element("soap:Body")
        action = ET.Element(method, self.ACTION_NS)
        body.append(action)

        for param, value in kwargs.items():
            element = ET.Element(param)
            element.text = str(value)
            action.append(element)

        envelope = ET.Element("soap:Envelope", self.BASE_NS)
        envelope.append(body)

        f = BytesIO()
        tree = ET.ElementTree(envelope)
        tree.write(f, encoding="utf-8", xml_declaration=True)

        return f.getvalue().decode("utf-8")


    async def _login(self):  # Login to device, and obtain credentials.

        resp = await self.call("Login", Action="request", Username=self.username, LoginPassword="", Captcha="")
        self.challenge = resp["Challenge"]
        self.public_key = resp["PublicKey"]
        self.cookie = resp["Cookie"]
        _LOGGER.debug("Challenge: %s, Public key: %s, Cookie: %s", self.challenge, self.public_key, self.cookie)

        self.private_key = _hmac(self.public_key + str(self.password), self.challenge)
        _LOGGER.debug("Private key: %s", self.private_key)

        _password = _hmac(self.private_key, self.challenge)

        resp = await self.call("Login", Action="login", Username=self.username, LoginPassword=_password, Captcha="")
        if resp["LoginResult"].lower() != "success":
            raise AuthenticationError("Login failed!")

        return


    async def call(self, action, *args, **kwargs):  # Update message, initiate request, and return action response.

        if action != "Login":
            _LOGGER.info("Logging into device at: %s", self.address)
            await self._login()

        _timestamp = int(datetime.now().timestamp())
        _data = self._generate_request_xml(action, **kwargs)

        _headers = self.headers.copy()
        _headers["SOAPAction"] = '"{0}{1}"'.format(self.ACTION_URL, action)

        if self.private_key:
            self.auth_token = _hmac(self.private_key, '{0}"{1}{2}"'.format(_timestamp, self.ACTION_URL, action))
            _LOGGER.debug("Generated new token for %s: %s (time: %d)", action, self.auth_token, _timestamp)

        if self.auth_token:
            _headers["HNAP_AUTH"] = "{0} {1}".format(self.auth_token, _timestamp)

        if self.cookie:
            _headers["Cookie"] = "uid={0}".format(self.cookie)

        resp = await self.session.post("http://{0}/HNAP1".format(self.address), data=_data, headers=_headers, timeout=10)
        text = await resp.text()

        if "soap:Envelope" in text:
            try:
                parsed = xmltodict.parse(text)
            except xml.parsers.expat.ExpatError:
                raise AuthenticationError("XML parser error!")
        else:
            raise AuthenticationError("Bad SOAP response!")

        return parsed["soap:Envelope"]["soap:Body"][action + "Response"]


def main():

    from datetime import datetime
    import json
    import urllib
    import smtplib
    import os.path
    import subprocess
    import http.client
    from time import sleep

    push_messages = list()
    day = datetime.now().day

    total_attempts = 3  # Any integer value greater than zero.


    async def post_request(address, password, action, state, **kwargs):

        #  Water Sensor
        #  ------------
        #  Action / State - GetWaterDetectorState / IsWater

        #  Siren
        #  ------------
        #  Action / State - SetSoundPlay / None, SetAlarmDismissed / None, Reboot / None, GetSirenAlarmSettings / IsSounding
        #  Sound Type     - 1 = Emergency, 2 = Fire, 3 = Ambulance, 4 = Police, 5 = Door Chime, 6 = Beep
        #  Volume         - 1 to 100
        #  Duration       - 1 to 88888

        session = aiohttp.ClientSession()

        i = 2
        while i > 0:
            try:
                client = HNAPClient(address, "Admin", password, loop=loop, session=session)
                resp = await client.call(action, ModuleID=1, **kwargs)

                if resp[action + "Result"].upper() != "OK":
                    raise AuthenticationError("Bad HNAP response!")
                else:
                    await session.close()
                    break

            except AuthenticationError:
                i -= 1
                _LOGGER.debug("Attempts remaining: %s", i)

                if i == 0:
                    await session.close()
                    raise AuthenticationError("Device not responding, assumed off-line!")

        return None if state == None else resp.get(state) == "true"


    if os.path.exists("smtp.json"):
        with open("smtp.json") as smtp_file:
            smtp = json.load(smtp_file)
    else:
        smtp = {"enabled": False}

    if os.path.exists("push.json"):
        with open("push.json") as push_file:
            push = json.load(push_file)
    else:
        push = {"enabled": False}

    if os.path.exists("ifttt.json"):
        with open("ifttt.json") as ifttt_file:
            ifttt = json.load(ifttt_file)
    else:
        ifttt = {"enabled": False}


    while True:

        if smtp["enabled"]:
            smtp_message = 'To: ' + smtp["recipient"] + '\n'
            smtp_message += 'From: ' + smtp["name"] + ' <' + smtp["sender"] + '>\n'
            smtp_message += 'Subject: ' + smtp["subject"] + '\n\n \n'
            smtp_message += 'Date: ' + datetime.now().strftime("%d-%b-%Y") + '\n'
            smtp_message += 'Time: ' + datetime.now().strftime("%H:%M:%S") + '\n\n'
            smtp_message += 'NOTE:\n\n'
        if push["enabled"] or ifttt["enabled"]:
            push_messages.clear()

        all_online = True
        save_siren = False
        save_sensor = False
        send_message = False

        if os.path.exists("siren.json"):  # Get address, pin, online, sound, volume and duration for siren.
            with open("siren.json") as siren_file:
                siren = json.load(siren_file)
        else:
            siren = {"enabled": False}

        if siren["enabled"]:  # If enabled, check if siren is on-line.

            on_line = not bool(subprocess.call(["ping", "-q", "-w 10", "-c 1", siren["address"]], stdout = subprocess.DEVNULL))
            if on_line:
                try:
                    loop = asyncio.get_event_loop()
                    if siren["test"]:
                        loop.run_until_complete(post_request(  # Test siren.
                            siren["address"], siren["pin"], "SetSoundPlay", None, SoundType=1, Volume=1, Duration=1
                        ))
                        siren["test"] = False
                        save_siren = True
                    status = loop.run_until_complete(post_request(  # Get siren status.
                        siren["address"], siren["pin"], "GetSirenAlarmSettings", "IsSounding"
                    ))
                    _LOGGER.info("Siren status: %s", status)
                except AuthenticationError:
                    on_line = False

            if on_line:
                if siren["online"] == 0:  # If previously off-line.
                    if smtp["enabled"]:
                        smtp_message += 'Siren connected to network!\n'
                    if push["enabled"] or ifttt["enabled"]:
                        push_messages.append('Siren connected to network!')
                    send_message = True

                if siren["online"] < total_attempts:  # Reset counter.
                    siren["online"] = total_attempts
                    save_siren = True
            else:
                if siren["online"] == 1:  # If previously on-line, and very last attempt failed.
                    if smtp["enabled"]:
                        smtp_message += 'Siren not connected to network!\n'
                    if push["enabled"] or ifttt["enabled"]:
                        push_messages.append('Siren not connected to network!')
                    send_message = True

                if siren["online"] > 0:  # Decrement counter.
                    siren["online"] -= 1
                    save_siren = True

                if siren["online"] == 0:  # If off-line.
                    all_online = False

            sleep(2)

        with open("config.json") as file:  # Get name, address, pin, online, and status for each sensor.
            data = json.load(file)

        for sensor in data["sensor"]:
            if sensor["enabled"]:

                on_line = not bool(subprocess.call(["ping", "-q", "-w 10", "-c 1", sensor["address"]], stdout = subprocess.DEVNULL))
                if on_line:
                    try:
                        loop = asyncio.get_event_loop()
                        status = loop.run_until_complete(post_request(  # Get water sensor status.
                            sensor["address"], sensor["pin"], "GetWaterDetectorState", "IsWater"
                        ))
                        _LOGGER.info("Sensor status: %s", status)
                    except AuthenticationError:
                        on_line = False

                if on_line:
                    if sensor["status"] != status:  # If sensor status has changed.
                        if not sensor["status"] and status:  # False --> True.
                            if smtp["enabled"]:
                                smtp_message += 'Water detected by ' + sensor["name"] + ' sensor!\n'
                            if push["enabled"] or ifttt["enabled"]:
                                push_messages.append('Water detected by ' + sensor["name"] + ' sensor!')

                            if siren["enabled"] and siren["online"] == total_attempts:
                                try:
                                    loop = asyncio.get_event_loop()
                                    loop.run_until_complete(post_request(  # Start siren.
                                        siren["address"], siren["pin"], "SetSoundPlay", None,
                                        SoundType=siren["sound"], Volume=siren["volume"], Duration=siren["duration"]
                                    ))
                                except AuthenticationError:
                                    if siren["online"] > 1:  # Decrement counter.
                                        siren["online"] -= 1
                                        save_siren = True

                        elif sensor["status"] and not status:  # True --> False.
                            if smtp["enabled"]:
                                smtp_message += 'Water no longer detected by ' + sensor["name"] + ' sensor.\n'
                            if push["enabled"] or ifttt["enabled"]:
                                push_messages.append('Water no longer detected by ' + sensor["name"] + ' sensor.')

                            if siren["enabled"] and siren["online"] == total_attempts:
                                try:
                                    loop = asyncio.get_event_loop()
                                    loop.run_until_complete(post_request(  # Stop siren.
                                        siren["address"], siren["pin"], "SetAlarmDismissed", None
                                    ))
                                except AuthenticationError:
                                    if siren["online"] > 1:  # Decrement counter.
                                        siren["online"] -= 1
                                        save_siren = True

                        sensor["status"] = status
                        save_sensor = True
                        send_message = True

                    if sensor["online"] == 0:  # If previously off-line.
                        if smtp["enabled"]:
                            smtp_message += sensor["name"] + ' water sensor connected to network!\n'
                        if push["enabled"] or ifttt["enabled"]:
                            push_messages.append(sensor["name"] + ' water sensor connected to network!')
                        send_message = True

                    if sensor["online"] < total_attempts:  # Reset counter.
                        sensor["online"] = total_attempts
                        save_sensor = True

                else:
                    if sensor["online"] == 1:  # If previously on-line, and very last attempt failed.
                        if smtp["enabled"]:
                            smtp_message += sensor["name"] + ' water sensor not connected to network!\n'
                        if push["enabled"] or ifttt["enabled"]:
                            push_messages.append(sensor["name"] + ' water sensor not connected to network!')
                        send_message = True

                    if sensor["online"] > 0:  # Decrement counter.
                        sensor["online"] -= 1
                        save_sensor = True

                    if sensor["online"] == 0:  # If off-line.
                        all_online = False

                sleep(2)

        sleep(10)

        if send_message:  # If device status has changed, send message(s) and/or save configuration.

            if smtp["enabled"]:
                server = smtplib.SMTP(smtp["server"], smtp["port"])
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp["userid"], smtp["password"])
                server.sendmail(smtp["sender"], smtp["recipient"], smtp_message)

            if push["enabled"]:
                for message in push_messages:
                    push_conn = http.client.HTTPSConnection("api.pushover.net:443")
                    push_conn.request("POST", "/1/messages.json",
                      urllib.parse.urlencode({
                        "token": push["token"],
                        "user": push["user"],
                        "title": push["title"],
                        "sound": push["sound"],
                        "message": message
                      }), { "Content-type": "application/x-www-form-urlencoded" })
                    push_conn.getresponse()

            if ifttt["enabled"]:
                for message in push_messages:
                    ifttt_conn = http.client.HTTPSConnection("maker.ifttt.com:443")
                    ifttt_conn.request("POST", "/trigger/" + ifttt["event"] + "/with/key/" + ifttt["key"],
                      ('{ "value1": \"' + ifttt["value1"] + '\", "value2": \"' + message + '\", "value3": \"' + ifttt["value3"] + '\" }'),
                      { "Content-type": "application/json" })
                    ifttt_conn.getresponse()

        if save_siren:
            with open("siren.json", "w") as file:
                json.dump(siren, file, indent=4)

        if save_sensor:
            with open("config.json", "w") as file:
                json.dump(data, file, indent=4)

        if all_online and day != datetime.now().day:  # If all devices are on-line, once per day place message in system log.
            day = datetime.now().day
            subprocess.call(["systemd-cat", "-t", "python", "echo", "Network: all devices on-line"])

        sleep(10)


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG)
    main()
