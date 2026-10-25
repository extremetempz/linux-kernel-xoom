# Image 73d: full WPA handshake logging

25 October 2026. 73c associates and the AP sends repeated 4-way M1 frames,
but the handshake does not complete. The current WPA log only captured the
first few seconds because it used `logcat -d` once.

73d changes only logging: logcat runs continuously for the whole session.

```sh
logcat -v time -s wpa_supplicant:* > /run/wpa-logcat.txt &
```

The driver and firmware are unchanged from 73c: native 4.4 bcmdhd, 40s
late load, Xoom OEM NVRAM, no explicit join chanspec.

## Image identity

- Path: `artifacts/androidgpu73d-ready/wingray-android44-gpu.img`
- Size: 4,202,496 bytes
- SHA-256: `a3651590d657acbe9ea6eb05fdd118783c8276f98d789a903a28a663dccd282c`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73d-ready/wingray-android44-gpu.img
fastboot reboot
```

Try Git Gud; when it reaches Connecting, wait 30 seconds, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73d-report1 \
  --storage-mode android44-readonly
```

`WPA_LOGCAT` will then show whether the supplicant sent M2 or logged a
pre-shared-key/handshake failure.
