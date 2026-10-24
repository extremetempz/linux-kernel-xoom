# Startup diagnostic 51: EMC correction and RAM-root localization

Prepared 25 October 2026. **Not yet hardware-tested. GPU acceleration remains
unproven.** The original ROM is running; a new test must pass fresh original-image
and power checks before a boot-only flash.

## Verified source defect and correction

Trace 50 recorded a zero old rate for both diagnostic EMC votes. In this Linux
4.4 CCF, `clk_core_get_rate_nolock()` returns zero for a clock without a parent
unless `CLK_IS_ROOT` is set. The Wingray diagnostic registers parentless software
votes without that flag. Patch 0100 adds it only to those two providers.

The regression test now compiles the actual CCF getter with the actual vote
registration/callbacks. The same nonzero cached rate is reported as zero when
the flag is removed, and correctly with the flag. Fault rollback, vote bounds,
physical-clock drift and exact engine aliases still pass. No physical EMC
setter is linked into this fixture or added by the correction. This establishes
the software defect; successful engine initialization on hardware still requires
a test. The clock-validation guard remains enabled.

## Separate unresolved boot failure

Trace 50 retained `VFS: Unable to mount`. It did not identify why `/init` was
unavailable. Offline inspection finds `/init`, the static BusyBox interpreter
and Android init in the generated archive; GNU cpio extracts those regular files
successfully. Device-node creation is unavailable to the unprivileged host test.
This does not establish that the bootloader supplied an intact initrd or that
the kernel unpacked it successfully. The EMC defect is not proven to cause the
root-mount panic.

Patch 0101 adds a separate cookie-51 diagnostic profile. Only that profile stops
with a specific retained panic prefix when:

- initramfs unpacking was explicitly skipped (`XOOM initrd skipped`);
- no usable external initrd reached rootfs population (`XOOM initrd absent`);
- the external archive unpacker returned an error (`XOOM unpack ...`);
- the early init path is inaccessible (`XOOM init access ...`, with full signed
  errno in the existing result word).

These checks prevent the RAM-only test from obscuring its first failure with a
later disk-root fallback. They do not alter memory layout, disk-root selection
in ordinary builds, ATAG conversion, image load addresses, or partition layout.
The cookie-49/50 profiles and tested DT/configurations remain preserved.

## Artifact and validation

Image: `artifacts/gpu-startup51-ready/wingray-gpu-render-diagnostic.img`

- SHA256: `a813af03a12216f5cdf228b58fc173f154186fcace617074c5a30871fca9bd7a`
- Size: 5,883,904 bytes; cookie `0x584d0051`.
- Ramdisk SHA256 unchanged from trace 50:
  `54bc23da30e3b4e17a87f461aac2e80bcf85bdbdcd17fc43230864f5a2b65c7a`.
- Nested kernel source: `aee49884` (EMC correction `dfb9cd63` separately committed).
- Complete ARM build and configuration/DT/symbol gates passed. Compiled outputs
  were compared byte-for-byte with the saved artifacts.
- Actual CCF/vote and nvhost clock transactions, diagnostic rootfs failure
  branches, retained writer/panic bounds for cookies 49/50/51, guarded readback
  fixtures, image payload checks and ARM reset emulation passed.
- The hardware description equals the previously prepared GPU DT; no Samsung
  board power/display/pinmux data was introduced.

Rendering is deliberately disabled, NVIDIA runtime is retained unchanged for
comparison, and there are no storage mounts. A successful startup test is the
next gate before any rendering retry. Flash only boot, collect USB or retained
startup evidence, restore the original boot, and verify complete boot/recovery
hashes. Preserve private raw logs and proprietary runtime files locally.
