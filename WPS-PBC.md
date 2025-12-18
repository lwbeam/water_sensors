# Bridged Access Point with WPS Push Button Configuration Support

## Introduction

Wi‑Fi Protected Setup (WPS) is a standard created by the Wi-Fi Alliance to simplify the connection of wireless devices to home and small office networks. The WPS protocol defines three types of devices in a wi-fi network: the _Registrar_, the _Enrollee_, and the _Access Point_. The _Registrar_ is a device with the authority to issue and revoke access to the network, and is usually integrated into the _Access Point_, but can be a separate device. The _Enrollee_ is the client device seeking to join the network. And the _Access Point_ functions as the proxy between the _Registrar_ and the _Enrollee_.

The WPS standard initially provided four methods of authenticating wi-fi client devices: PIN, Push Button, Near-field, and USB. Only the PIN and Push Button methods are currently covered by the WPS certification, and the USB method has since been deprecated. A major security flaw was identified in December 2011, that affects wi-fi routers with the WPS PIN feature. At that time most router models had this feature enabled by default. This flaw allows a remote attacker to recover the WPS PIN using a brute-force attack, in as little as four hours. As a result, users were repeatedly urged to disable the WPS PIN feature. Unfortunately, over time this message has _evolved_ to the point where it's now widely believed that, on the whole, WPS is insecure. However, **this is not the case**.

To initiate Push Button Configuration, the user must press a physical or _virtual_ button on both the access point and the wi-fi client device. On most devices this discovery mode disables itself as soon as a connection has been established, or after a delay (typically two minutes or less), whichever comes first, thereby minimizing the potential attack exposure time. Furthermore, most access points refuse to establish a connection when more than one client device, seeking to join the network, has been detected. This further minimizes the likelihood of a successful attack. As a result, an attacker must either have physical access to the access point, if it incorporates a physical button, or have as a minimum _user privileges_, in order to access a _virtual_ button. The former can be mitigated by physically securing the device. The latter obviates such an attack.

The following sections provide detailed command line instructions for the configuration of a Raspberry Pi single board computer as a bridged access point with support for WPS Push Button Configuration (WPS-PBC). As there have been significant changes made to the manner in which networking is configured and managed, during the last two major Raspberry Pi OS releases, specific instructions are provided for Bullseye (Debian 11), Bookworm (Debian 12), and Trixie (Debian 13).

## _hostapd_ vs _wpa_supplicant_

Generally speaking, wi-fi local area networks are comprised of two types of components: _Access Points_ (AP) or hosts, and _Stations_ (STA) or clients. _hostapd_ and _wpa_supplicant_ are open-source Linux packages, commonly used to configure and manage wi-fi network hosts and clients, respectively. Each package includes a user space back-end daemon, that can be run in the background or as a service, as well as text-based and graphical user interface front-end tools. These two packages are currently maintained by the same [individual](https://w1.fi/) and group of contributors.

### _hostapd_

_hostapd_ is used to configure and manage access points and authentication servers. Among other things, it implements IEEE 802.11 access point management, IEEE 802.1X/WPA/WPA2/WPA3/EAP Authenticators, an EAP server, and a RADIUS authentication server. In addition to WPA/IEEE 802.11i/EAP/IEEE 802.1X standards, _hostapd_ provides support for many Extensible Authentication Protocol (EAP) methods, and the [WPS](https://git.w1.fi/cgit/hostap/tree/hostapd/README-WPS) standard. As a result, an access point can be configured to allow access to a wi-fi network via WPS, using the associated text-based tool, `hostapd_cli`. For more information regarding `hostapd_cli`, see its [man page](https://manpages.debian.org/trixie/hostapd/hostapd_cli.1.en.html) and associated `help` command.

_hostapd_ behaviour is controlled via its configuration file. A complete explanation of the _hostapd_ configuration file, including all available options, can be found [here](https://git.w1.fi/cgit/hostap/plain/hostapd/hostapd.conf).

### _wpa_supplicant_

A _Supplicant_ is the IEEE 802.1X/Wi-Fi Protected Access (WPA) component used to manage wi-fi network clients. _wpa_supplicant_ implements security key negotiation with WPA _Authenticators_, and controls the roaming and IEEE 802.11 authentication/association of the wi-fi network driver. In addition to the WPA, WPA2 (IEEE 802.11i/RSN), and WPA3 security protocols, it provides support for the [WPS](https://git.w1.fi/cgit/hostap/tree/wpa_supplicant/README-WPS) standard. As a result, a client can be configured to request access to a wi-fi network via WPS, using the associated text-based tool, `wpa_cli`. For more information regarding `wpa_cli`, see its [man page](https://manpages.debian.org/trixie/wpasupplicant/wpa_cli.8.en.html) and associated `help` command.

_wpa_supplicant_ behaviour can be controlled via its configuration file, which includes a number of global parameters, and one or more network blocks. Each network block specifies the credentials and options for each host, to which the client can request access. One such option is the _IEEE 802.11 operation mode_, which can be set to: `0` (infrastructure), `1` (ad-hoc or peer-to-peer), or `2` (access point). Placing `mode=2` in a network block will cause _wpa_supplicant_ to configure the specified wi-fi network interface as an access point. However, an access point created in this manner retains the WPS features of a client (i.e., it can seek, but not grant wi-fi network access). A complete explanation of the _wpa_supplicant_ configuration file, including all available options, can be found [here](https://git.w1.fi/cgit/hostap/plain/wpa_supplicant/wpa_supplicant.conf).

For Bullseye (Debian 11), the _wpa_supplicant_ daemon is deployed as a service, with the configuration file, `/etc/wpa_supplicant/wpa_supplicant.conf`, accessible to the user. For Bookworm (Debian 12) and Trixie (Debian 13), _NetworkManager_ has become the default network management tool, which uses the _wpa_supplicant_ daemon as its back-end to manage wi-fi network connections. As a consequence, the _wpa_supplicant_ daemon is not deployed as a service, and the configuration file is not accessible to the user. Futhermore, the ability of _NetworkManager_ to configure and manage a wi-fi network interface as an access point, is limited by that of _wpa_supplicant_.

## Before Starting

**a.** Ensure that the Raspberry Pi OS is up-to-date.

```
sudo apt update

sudo apt full-upgrade

sudo apt autoremove
```

**b.** Ensure that the **country code**, **locale**, and **timezone** have been configured correctly. The wi-fi network interface will not be enabled until a **country code** has been set. These can be configured using _Raspberry Pi Imager_ and/or _raspi-config_.

**c.** **DO NOT** configure the wi-fi network interface, **in any way**, using _Raspberry Pi Imager_, _wpa_supplicant_, or _NetworkManager_. Doing so will interfere with the ability of _hostapd_ to control it.

## Bullseye (Debian 11)

### 1. Install and Configure _hostapd_ Daemon

**a.** Install the _hostapd_ package.

```
sudo apt install hostapd
```

**b.** Create a WPS client pre-shared key (PSK) file. This file is not created by _hostapd_, but must pre-exist for WPS-PBC to function.

```
sudo touch /etc/hostapd.wpa_psk
```

**c.** Create the _hostapd_ configuration file `/etc/hostapd/hostapd.conf` using the following as a template. The `<SSID>` and `<PASSWORD>` must be provided for the access point being setup. As presented, `channel` is set to `6`. Valid `channel` options will depend on the country code (set via _raspi-config_), with `0` enabling automatic channel selection. Finally, `max_num_sta` can be used to limit the number of client devices allowed to connect to the access point. As presented, `max_num_sta` is set to `6`, but may be increased to a maximum of nineteen (see **Step d**). For more information, see the complete configuration file `/usr/share/doc/hostapd/examples/hostapd.conf` provided with the package.

```
# Configure network interface and driver
interface=wlan0
bridge=br0
driver=nl80211

# AP WPA2-Personal configuration
hw_mode=g
channel=6
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
max_num_sta=6
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
ssid=<SSID>
wpa_passphrase=<PASSWORD>

# Enable random per-device PSK generation for WPS clients (file must exist)
wpa_psk_file=/etc/hostapd.wpa_psk

# Enable control interface (required for hostapd_cli)
ctrl_interface=/var/run/hostapd

# Enable internal EAP server (required for WPS)
eap_server=1

# WPS configuration (AP configured, disallow external WPS registrars)
wps_state=2
ap_setup_locked=1
device_type=6-0050F204-1
config_methods=virtual_push_button
```

<a name="hostapd-ifupdown-method"></a>
> **NOTE:** There is no need to `unmask` and `enable` the _hostapd_ service, as the _ifupdown_ method is being used to manage the _hostapd_ process (see `/usr/share/doc/hostapd/README.Debian`).

**d.**  As discussed [here](https://github.com/RPi-Distro/firmware-nonfree/issues/49), there is an issue with Broadcom/Cypress wi-fi firmware **cyfmac43455** (Version: 7.45.241, Date: 2021-11-01), used by Raspberry Pi 3B+ and later models. This issue can result in IOT devices becoming disassociated from the access point. It is not known if the Broadcom/Cypress firmware used by other Raspberry Pi models is similarly afflicted. However, this issue also exists with the latest version of the cyfmac43455 firmware available at the time of writing (Version: 7.45.286, Date: 2024-10-28).

Furthermore, the Wi-Fi chips used by these Raspberry Pi models have limited memory, and as a result, the _standard_ version of the Wi-Fi firmware is only able to act as an access point for a maximum of six clients. By removing some features, a _minimal_ version of the cyfmac43455 firmware has been created to handle up to nineteen clients.
If either of these issues are encountered, try using the _minimal_ version of this firmware.

```
sudo update-alternatives --set cyfmac43455-sdio.bin /lib/firmware/cypress/cyfmac43455-sdio-minimal.bin
```

### 2. Configure Network Bridge

Every effort has been made to provide a method that does not employ obsolete or deprecated packages, such as _bridge-utils_. However, as discussed [here](https://serverfault.com/questions/1153694/debian-create-persistent-network-bridge), in addition to the utilities replaced by those provided in the _iproute2_ package, such as _ip addr_ and _ip route_, the _bridge-utils_ package also contains _ifupdown_ hooks required to create a bridge network interface. As these hooks have never been migrated to a separate package, the only means of installing them is via the _bridge-utils_ package.

**a.** Install the _bridge-utils_ package.

```
sudo apt install bridge-utils
```

**b.** Configure the bridge network interface by placing the following in one or more network configuration files. The entire configuration can **EITHER** be appended to the existing `/etc/network/interfaces` file, **OR** placed in **one** (containing the entire configuration) **or more** files (one interface configuration in each file), located in the `/etc/network/interfaces.d/` directory, with whatever filenames that make sense.

```
# Loopback Interface
auto lo
iface lo inet loopback

# Ethernet Interface
auto eth0
iface eth0 inet manual

# Wi-Fi Interface
allow-hotplug wlan0
iface wlan0 inet manual

# Bridge Interface (dynamic address)
auto br0
iface br0 inet dhcp
    hostapd /etc/hostapd/hostapd.conf
    bridge_ports eth0
```

> **NOTE:** The wi-fi network interface `wlan0` does not need to be explicitly included in the list of `bridge_ports`, as the `bridge=br0` parameter in the _hostapd_ configuration file ensures that it will be added to the bridge network interface. Furthermore, contrary to conventional wisdom, _dhcpcd_ does not need to be disabled or reconfigured in anyway, as doing so will interfere with IP address assignment by the upstream dhcp server. Finally, for more information regarding the contents of this configuration file, see the associated _ifupdown_ package examples file `/usr/share/doc/ifupdown/examples/network-interfaces`.

**c.** To provide the Raspberry Pi with a static IP address **(optional)**, replace the **Bridge Interface** stanza presented above with the following, once `address`, `broadcast`, `gateway` and `dns-nameservers` have been updated with the appropriate IP addresses.

```
# Bridge Interface (static address)
auto br0
iface br0 inet static
    hostapd /etc/hostapd/hostapd.conf
    bridge_ports eth0
    address 192.168.X.XXX/24
    broadcast 192.168.X.255
    netmask 255.255.255.0
    gateway 192.168.X.1
    dns-nameservers XXX.XXX.XXX.XXX XXX.XXX.XXX.XXX
```

**d.** Re-start the _networking_ service.

```
sudo systemctl daemon-reload

sudo systemctl restart networking
```

> **NOTE:** The IP address for the Raspberry Pi may appear to <ins>remain unchanged</ins>, even if a different static IP address has been set, as the ethernet network interface `eth0` retains its original dynamically-assigned IP address, and the static IP address is assigned to the network bridge interface. Allowing one of the network interfaces to have a dynamically-assigned IP address is the safest configuration, as the Raspberry Pi will always be assigned a valid IP address, even when it has been moved to a network with a different subnet range. Finally, if there is a valid reason for both network interfaces being assigned a static IP address, only one can act as the gateway (i.e., only provide an `address` for the second network interface).

### 3. Connect Device to Wi-Fi Network

**a.** Initiate the WPS-PBC process on the access point (equivalent to pushing the WPS button on a router).

```
sudo hostapd_cli wps_pbc
```

> **NOTE:** If you don't get the following response, something has gone wrong.

```
Selected interface 'wlan0'
OK
```

**b.** Push the WPS button on the client device. If the device is within range of the access point, it should connect to the network, and be assigned an IP address by the upstream DHCP server.

## Bookworm (Debian 12)
With the introduction of Bookworm (Debian 12), _NetworkManager_ has become the default network management tool, essentially replacing the _ifupdown_ and _dhcpcd_ packages. This has resulted in three major changes to the method previously used to create a bridged access point. First, although _NetworkManager_ includes an _ifupdown_ plugin, this plugin is only able to <ins>read</ins> connection settings from the `/etc/network/interfaces` file, and only those for the wi-fi and ethernet network interfaces. As a result, the _NetworkManager_ text user interface and command-line interface tools (`nmtui` and `nmcli`) must be used to manage the network interface connections. Second, _NetworkManager_ uses _wpa_supplicant_ as its back-end to manage the wi-fi network interface, including _access point mode_. Furthermore, there is no means provided to directly configure or disable _wpa_supplicant_. As a result, _NetworkManager_ **must not** be used to configure the wi-fi network interface, so as to ensure that it does not interfere with the _hostapd_ daemon. Third, the [_ifupdown_ method](#hostapd-ifupdown-method) can no longer be used to manage the _hostapd_ daemon, and as a result, it must be initiated as a system service. This requires another work-around to ensure that the _hostapd_ daemon always starts after a system re-boot. And finally, yet another minor work-around is required to address an issue associated with the Broadcom/Cypress Wi-Fi firmware, that has been included with Bookworm (Debian 12) for the Raspberry Pi 3B+ and later models.

### 1. Configure Network Bridge

**a.** Create bridge connection _Bridge_ with network interface name `br0`.

```
sudo nmcli con add type bridge con-name 'Bridge' ifname br0
```

**b.** Create bridge slave connection _Ethernet_, using network interface `eth0`, and add it to the _Bridge_ connection.

```
sudo nmcli con add type bridge-slave con-name 'Ethernet' ifname eth0 master br0
```

**c.** To provide the Raspberry Pi with a static IP address **(optional)**, modify the _Bridge_ connection with the appropriate `ipv4.addresses`, `ipv4.gateway` and `ipv4.dns` IP addresses.

```
sudo nmcli con mod 'Bridge' \
    ipv4.addresses '192.168.X.XXX/24' \
    ipv4.gateway '192.168.X.1' \
    ipv4.dns 'XXX.XXX.XXX.XXX','XXX.XXX.XXX.XXX' \
    ipv4.method 'manual' \
    ipv4.may-fail false
```

**d.** Activate _Bridge_ connection.
```
sudo nmcli con up Bridge
```
### 2. Install and Configure _hostapd_ Daemon

**a.** Install the _hostapd_ package.

```
sudo apt install hostapd
```

**b.** Create the WPS client pre-shared key (PSK) file. This file is not created by _hostapd_, and must pre-exist for WPS-PBC to function.

```
sudo touch /etc/hostapd.wpa_psk
```

**c.** Prepare the _hostapd_ service to be configured and started.

```
sudo systemctl unmask hostapd
```

**d.** Create the _hostapd_ configuration file `/etc/hostapd/hostapd.conf` using the following as a template. The `<SSID>` and `<PASSWORD>` must be provided for the access point being setup. As presented, `channel` is set to `6`. Valid `channel` options will depend on the country code (set via _raspi-config_), with `0` enabling automatic channel selection. Finally, `max_num_sta` can be used to limit the number of client devices allowed to connect to the access point. As presented, `max_num_sta` is set to `6`, but may be increased to a maximum of nineteen (see **Step f**). For more information, see the complete configuration file `/usr/share/doc/hostapd/examples/hostapd.conf` provided with the package.

```
# Configure network interface and driver
interface=wlan0
bridge=br0
driver=nl80211

# AP WPA2-Personal configuration
hw_mode=g
channel=6
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
max_num_sta=6
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
ssid=<SSID>
wpa_passphrase=<PASSWORD>

# Enable random per-device PSK generation for WPS clients (file must exist)
wpa_psk_file=/etc/hostapd.wpa_psk

# Enable control interface (required for hostapd_cli)
ctrl_interface=/var/run/hostapd

# Enable internal EAP server (required for WPS)
eap_server=1

# WPS configuration (AP configured, disallow external WPS registrars)
wps_state=2
ap_setup_locked=1
device_type=6-0050F204-1
config_methods=virtual_push_button
```

**e.** As discussed [here](https://forums.raspberrypi.com/viewtopic.php?t=234145), the _hostapd_ service may not always start after a re-boot. To ensure that it does, add `ExecStartPre=/bin/sleep 10` to the **[Service]** section of the `/etc/systemd/system/multi-user.target.wants/hostapd.service` file.

```
sudo nano /etc/systemd/system/multi-user.target.wants/hostapd.service

    ExecStartPre=/bin/sleep 10
```

**f.**  As discussed [here](https://github.com/RPi-Distro/firmware-nonfree/issues/49), there is an issue with Broadcom/Cypress wi-fi firmware **cyfmac43455** (Version: 7.45.241, Date: 2021-11-01), used by Raspberry Pi 3B+ and later models. This issue can result in IOT devices becoming disassociated from the access point. It is not known if the Broadcom/Cypress firmware used by other Raspberry Pi models is similarly afflicted. However, this issue also exists with the latest version of the cyfmac43455 firmware available at the time of writing (Version: 7.45.286, Date: 2024-10-28).

Furthermore, the Wi-Fi chips used by these Raspberry Pi models have limited memory, and as a result, the _standard_ version of the Wi-Fi firmware is only able to act as an access point for a maximum of six clients. By removing some features, a _minimal_ version of the cyfmac43455 firmware has been created to handle up to nineteen clients.
If either of these issues are encountered, try using the _minimal_ version of this firmware.

```
sudo update-alternatives --set cyfmac43455-sdio.bin /lib/firmware/cypress/cyfmac43455-sdio-minimal.bin
```

**g.** Enable and start the _hostapd_ service.

```
sudo systemctl enable hostapd

sudo systemctl start hostapd

sudo reboot
```

> **NOTE:** The IP address for the Raspberry Pi **will change** following the re-boot. This is due to the fact that the _Bridge_ connection is dynamiically-assigned a new IP address based on the MAC address of the `wlan0` network interface. Unlike Bullseye (Debian 11), there does not appear to be any way for the `eth0` network interface to retain the ability to have a dynamically-assigned IP address. Even if a new ethernet connection is created and activated, it is deactivated following the next re-boot, and no IP address is assigned. Finally, creating the `br0` network interface adds approximately 30 seconds to the Raspberry Pi boot time. It will now feel painfully long.

### 3. Connect Device to Wi-Fi Network

**a.** Initiate the WPS-PBC process on the access point (equivalent to pushing the WPS button on a router).

```
sudo hostapd_cli wps_pbc
```

> **NOTE:** If you don't get the following response, something has gone wrong.

```
Selected interface 'wlan0'
OK
```

**b.** Push the WPS button on the client device. If the device is within range of the access point, it should connect to the network, and be assigned an IP address by the upstream DHCP server.

## Trixie (Debian 13)

With the introduction of Trixie (Debian 13), _cloud-init_ and _netplan_ have been added to the network configuration and management process. As discussed [here](https://github.com/raspberrypi/trixie-feedback/issues/3#issuecomment-3376485383), the addition of _netplan_ as the front-end for _NetworkManager_ was necessary to factiliate the new customization provisioning system, which is based on _cloud-init_. For the average user, these changes will have little or no impact, as _NetworkManager_, and its associated tools (`nmtui` and `nmcli`), function as they did in Bookworm (Debian 12). For more information, see this [News](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/) post.

To configure a bridged access point in Trixie (Debian 13), use the method presented above for Bookworm (Debian 12). Based on initial testing, **Step 2 e** may be skipped; however, doing so appears to have little impact on the boot time.

## Troubleshooting _hostapd_

https://github.com/raspberrypi/linux/issues/6885

## References

https://w1.fi/hostapd/

https://git.w1.fi/cgit/hostap/plain/hostapd/README-WPS

https://wifitutorialspoint.com/Linux/linux-wireless-testing/wi-fi-security/wps-pbc/wps-pbc.html

https://manpages.debian.org/trixie/ifupdown-ng-compat/interfaces.5.en.html

https://thelinuxcode.com/debian_etc_network_interfaces

https://unix.stackexchange.com/questions/128439/good-detailed-explanation-of-etc-network-interfaces-syntax

https://www.cyberciti.biz/faq/setting-up-an-network-interfaces-file

https://thelinuxcode.com/reload-network-interfaces-debian

https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html

https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html

https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/
