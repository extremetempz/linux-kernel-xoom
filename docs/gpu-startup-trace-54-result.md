# Startup diagnostic 54: built-in runtime and engines start

Hardware test/readback recorded 25 October 2026 (client timezone). **Two fresh,
integrity-verified USB reports confirm startup of the RAM runtime and successful
GR2D/GR3D driver initialization. Rendering was deliberately disabled.**

- Original Android init supplied a property workspace; startup reported
  `XOOM_GPU_STARTUP_DEVICES_READY` and `XOOM_GPU_STARTUP_ONLY_DONE`.
- `/dev/nvhost-ctrl`, `/dev/nvhost-gr2d`, `/dev/nvhost-gr3d`, `/dev/nvmap` and
  `/dev/tegra_sema` are present. Both engine initcalls returned 0.
- The physical EMC rate reports 600 MHz. Software votes report nonzero rates;
  the prior zero-rate CCF registration rejection is no longer blocking startup.
- The retained record has cookie `0x584d0054`, host/GR2D/GR3D stage 61/result 0,
  CPU1 online, kernel stage 7/exec result 0, USB registration result 0 and no
  retained panic. Trace SHA256: `21c52fad7d1bb8bcb4b874c4e82416e49cdbd5b610531689cb0e440034ceeedf`.
- Userspace/reporter retained markers remained zero despite the independently
  verified live reports. Do not interpret their absence alone as no userspace.
- The tiny external initrd still logs `junk in compressed archive`. Built-in
  runtime preserved a usable root and startup continued. Its success bypasses
  the external-input problem; it does not locate the corruption point.
- eMMC capacity and all ten BigPart partition extents match the original reference;
  captured storage mode is virtual-only, with no persistent storage mounts.

Report SHA256 values: `0884ef970747e0888ea23aaead6419905392d0e94a6be1b1e04ad28fbb95edde` and
`959800681d5f1ed816e8fcd07a84016ad730a9e3e7771014d6fd875b3facc347`. They used separate fresh nonces; private raw reports
remain under `artifacts/gpu-startup54-report1/` and `gpu-startup54-report2/`.

## Limits and next step

Engine publication and startup are not GPU job execution or rendered pixels.
The offscreen probe was disabled, so Linux 4.4 acceleration remains unproven.
Next use the already-tested bounded NVIDIA two-frame probe as a disposable child
with the built-in runtime, retaining fixed clocks, RAM-only storage and USB
reporting. Do not infer working gralloc/HWC/Android composition from this result.

The report includes a nonfatal pre-existing `fsync_enabled` sysfs permission
warning and an early GPIO registration failure/retry message. Neither prevented
this isolated startup. They are not established causes of the earlier root stop.

## Device preservation

Original boot was restored, Android returned over ADB after the requested minute,
and complete boot/recovery hashes match the original backups. The guarded readback
completed, its temporary RAM reader was removed, and no new fault was detected in
the original kernel-log comparison. No restoration remains pending. Private test
state and retained record are in `artifacts/gpu-startup54-attempt1/`.
