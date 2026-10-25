# Image 73g: legacy WLC_SET_SSID join

25 October 2026. 73f's explicit 20 MHz channel was still sent through the
newer **`join` iovar**, which the 4.218 firmware does not support:

```text
WLC_SET_VAR: join, UNSUPPORTED
nl80211: MLME connect failed: ret=-20 (Not a directory)
```

73g always uses the legacy join path:

```c
WLC_SET_SSID
```

with a plain 20 MHz chanspec. This is the path the original Xoom firmware
understands, and it accepts the explicit channel so association completes
within the supplicant's 10-second timeout.

The driver still reports the connect result on `WLC_E_ASSOC`.

## Image identity

- Path: `artifacts/androidgpu73g-ready/wingray-android44-gpu.img`
- Size: 4,200,448 bytes
- SHA-256: `3ccd02ef29e83d2e071c6a5f9705e14d31a2ba84a6456f6bca82887fcd46f5d4`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73g-ready/wingray-android44-gpu.img
fastboot reboot
```

Connect to Git Gud or the hotspot, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73g-report1 \
  --storage-mode android44-readonly
```

Expected: no `join, UNSUPPORTED`, fast association, `CTRL-EVENT-CONNECTED`,
4-way handshake and DHCP.
