# Image 59 stop and image 60 framebuffer bus-map correction

25 October 2026. Image 59 was flashed boot-only. A fresh, nonce/integrity-verified USB report confirmed matching full-capacity/all-ten BigPart storage, Android ABI exit 0 and two-core handoff exit 0. Its bootstrap stopped at `FAILED_display`, before executing Android init.

The kernel logged:

```text
tegradc tegradc.0: no fb_mem resource
tegradc: probe of tegradc.0 failed with error -2
```

The compiled DT contains the named framebuffer `reg` entry, but its parent host bus inherits only `ranges = <0x54000000 0x54000000 0x04000000>`. Physical fb0 at `0x2e800000` is outside that range. The donor's resource-count loop calls `of_address_to_resource` successively and stops when this second register cannot translate, leaving no fbmem resource. This is an address-translation failure, not evidence of an engine, panel-voltage or touch failure.

The first raw-DT ownership gate checked the reservation but missed the bus translation. The regression now compiles Linux's actual `of_bus_default_map` function: the old range rejects fb0; the correction translates both boundaries of the exact existing 8 MiB reservation, rejects either neighbor and the nvmap heap, and preserves engine MMIO translation.

## Isolated correction

Patch 0111 (`3268a272`) adds separate `wingray_android44_gpu_fbmap_defconfig` and `tegra20-motorola-wingray-android44-gpu-fbmap.dts`. The only hardware-description change relative to 59 is the added identity bus range:

```text
0x2e800000 -> 0x2e800000, length 0x00800000
```

It retains the original `0x54000000` register range. The new profile has fresh trace cookie `0x584d0060`; the failed 59 profile and artifact remain intact. The Android built-in archive is byte-identical to image 59. No panel timing, power, pinmux, GPU clock, allocation range or userspace-overlay change is mixed into this correction.

The artifact gate now checks the bus range, accepts the corrected profile for packaging and rejects known-failed 59 for new packaging. Guarded historical trace retrieval remains possible with the corresponding artifact validator. Actual linked archive/compressed kernel bytes and conservative boot footprint checks pass, as do ARM reset/retained-trace guards for the new cookie.

Image 60: `artifacts/androidgpu60-ready/wingray-android44-gpu.img`, 3,635,200 bytes, SHA-256 `676e5beb7ac2cf3d6debc8507e2ff8b398f0659bccdb3aca80b837f1527c71ac`.

The user explicitly requested staying in fastboot and flashing the correction without an intermediate original-ROM boot. Accordingly image 60 was flashed to boot only and rebooted. Original restoration remains pending at this preparation checkpoint; recovery/layout were not written. Hardware outcome is not established by these offline checks. The correction and this evidence were committed after the flash as requested. GitHub publication is deferred by the user's explicit instruction following its HTTP upload failure.
