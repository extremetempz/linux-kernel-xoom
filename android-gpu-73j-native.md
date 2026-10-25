# Image 73j: define dhcpcd_wlan0

25 October 2026. Wi-Fi association and the WPA2 four-way handshake now
complete:

```text
CTRL-EVENT-CONNECTED - Connection to 18:e8:29:4b:5e:6a completed
EAPOL authentication completed successfully
```

But DHCP never starts:

```text
init: no such service 'dhcpcd_wlan0'
init: no such service 'dhcpcd_wlan0:-f /system/etc/dhcpcd/dhcpcd.conf -h ... wlan0'
```

Android's `DhcpStateMachine` starts the exact service name **`dhcpcd_wlan0`**,
appending its own `-f`/`-h`/interface arguments. The initramfs only defined
a generic `dhcpcd` service, so Android could not request a lease.

73j adds:

```text
service dhcpcd_wlan0 /system/bin/dhcpcd -aABKL
    class main
    disabled
    oneshot
```

## Image identity

- Path: `artifacts/androidgpu73j-ready/wingray-android44-gpu.img`
- Size: 4,122,624 bytes
- SHA-256: `9d4465a7cc62286de80a37b0d0b9b83d1ebe79dbcf41161e6f0cb30532635827`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73j-ready/wingray-android44-gpu.img
fastboot reboot
```

Connect to Git Gud, wait for the IP address, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73j-report1 \
  --storage-mode android44-readonly
```

Expected: `dhcpcd_wlan0` starts, wlan0 gets an IPv4 address, and the Wi-Fi
icon shows a connection.
