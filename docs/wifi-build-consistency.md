# Wi-Fi build consistency check

25 October 2026.

## Image 73g module

The module shipped in Image 73g is the module produced by its build:

```text
artifacts/androidgpu73g-runtime/modules/bcmdhd.ko   1bcb3a09338f609d7ed099493b53815f9fa59e7aebb59aeccb097d6fb2401b55
build/out/.../bcmdhd.ko (stripped)                 1bcb3a09338f609d7ed099493b53815f9fa59e7aebb59aeccb097d6fb2401b55
```

The build script strips the module after copying it, which is why the raw
build object has a different hash.

## Reproduction

- `sources/kernel-donor/arch/arm/configs/wingray_android44_gpu_fbmap_defconfig`
  now selects `CONFIG_BROADCOM_WIFI=y` and the native driver paths.
- `scripts/build-android-gpu.sh` selects the native driver and copies
  `drivers/net/wireless/bcmdhd/bcmdhd.ko`.
- `scripts/prepare-android-gpu.py` stages the Xoom OEM calibration, the
  native `nl80211` supplicant, continuous WPA logging, and no custom WEXT
  binary.
- `tests/test-wingray-wifi.py` checks the native driver, `WLC_E_ASSOC`
  connect result, 20 MHz chanspec, `WLC_SET_SSID`, OEM NVRAM and the
  exported patch series.
- `kernel/patches/0138-*` and `0139-*` export the native module name and
  the final association/join code. The obsolete legacy drivers and patches
  have been removed.

The series applies cleanly to the pinned donor
`bbcece6d21c83b6280061a91d27566aff1951c94`.

## Current functional blocker

Image 73g still fails association immediately:

```text
nl80211: MLME connect failed: ret=-20 (Not a directory)
wlan0: Association request to the driver failed
```

There is no `Connecting with ...` line from `wl_cfg80211_connect`, so the
failure occurs before the join path that 73g changed. It is not a stale
module and not the old TF101 path. The next diagnostic step is to log or
breakpoint the early connect setters, not to keep changing the join command.
