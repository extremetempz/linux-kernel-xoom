> **Superseded by Image 73g.** 73f still used the unsupported `join`
> iovar. Use `android-gpu-73g-native.md`.

# Image 73f: explicit 20 MHz join channel

25 October 2026. 73e correctly reported the connect result on
`WLC_E_ASSOC`, but association itself took ~22 seconds because the join
scanned every channel. wpa_supplicant's hard-coded authentication timeout
is 10 seconds, so it timed out and disconnected before the firmware
finished.

The original explicit-channel attempt failed with `BCME_BADCHAN` because
the newer host driver built an 80 MHz chanspec. 73f restores the explicit
channel and forces a plain 20 MHz chanspec:

```c
bw = WL_CHANSPEC_BW_20;
```

This makes the join fast and acceptable to the 4.218 firmware.

## Image identity

- Path: `artifacts/androidgpu73f-ready/wingray-android44-gpu.img`
- Size: 4,200,448 bytes
- SHA-256: `4242da2c923c790b216dc2342b6b5425a3939e8e7c11ceb2f6d2e29fed9848a9`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73f-ready/wingray-android44-gpu.img
fastboot reboot
```

Connect to Git Gud or the hotspot, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73f-report1 \
  --storage-mode android44-readonly
```

Expected: association completes quickly, `CTRL-EVENT-CONNECTED`, 4-way
handshake, then DHCP.
