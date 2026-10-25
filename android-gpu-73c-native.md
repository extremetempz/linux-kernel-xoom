# Image 73c: no explicit join chanspec

25 October 2026. 73b scans correctly (7 BSSes) but association failed:

```text
nl80211: MLME connect failed: ret=-20
wlan0: Association request to the driver failed
```

`-20` is Broadcom `BCME_BADCHAN`. The 4.4 host driver sends an explicit
join chanspec (built by the newer host code) to the ROM's 4.218 firmware,
which rejects it.

73c ignores the user-supplied join channel and sets `chanspec_num=0`, so
the firmware joins by scanning all supported channels:

```c
chan = NULL;
chan_cnt = 0;
cfg->channel = 0;
```

Everything else remains 73b: native 4.4 `bcmdhd.ko`, late load, Xoom OEM
NVRAM, Android nl80211 supplicant.

## Image identity

- Path: `artifacts/androidgpu73c-ready/wingray-android44-gpu.img`
- Size: 4,202,496 bytes
- SHA-256: `14e25e015c0311a8dbf4239b08795cf8bcb25ee7f5a06716ab3206ca52c4f6f4`

## Test

```sh
cd /home/justin/linux-kernel-xoom
fastboot flash boot /home/justin/linux-kernel-xoom/artifacts/androidgpu73c-ready/wingray-android44-gpu.img
fastboot reboot
```

Connect to Git Gud, then capture:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu73c-report1 \
  --storage-mode android44-readonly
```

Expected: `Trying to associate` is no longer followed by `BCME_BADCHAN`,
then 4-way handshake and DHCP.
