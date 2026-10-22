# Android lockscreen checkpoint — 22 October 2026

## Verified milestone

Image 29 displayed RGB bars on the physical MZ604; the operator confirmed seeing them. USB reports also verified the framebuffer/backlight, full eMMC capacity and all ten BigPart extents. See `trace-boot-attempt-29.md` for evidence and limitations. Android has not started under the new kernel.

The original boot image was restored after that test. Complete boot and recovery readbacks matched their preserved originals, and the working Android ROM returned. No image 30 has been flashed. Backups, device identifiers, private captures and compiled binaries are excluded from this commit.

## Next kernel: built, not hardware tested

The donor kernel has four separate source commits, exported as patches 0051–0054:

- `b0908a66`: isolated Android 4.4 profile with legacy 32-bit Binder protocol 7, ashmem, cgroups and core sockets.
- `def54382`: explicitly scoped Wingray first-boot profile marks eMMC read-only before exposing disks.
- `611dba55`: the same profile rejects raw MMC command ioctls before payload decoding.
- `58633a85`: ports the working KitKat logger ABI to the 4.4 write-iterator interface.

The kernel at donor HEAD `58633a85` compiled successfully and passed the configuration/DT/symbol verifier. Host tests exercised the actual first-boot scope and ioctl dispatch, and the logger write path with fault, wrap and concurrency cases. These checks do not prove target Android compatibility or physical write protection.

## Incomplete integration, deliberately saved as draft

The Android bootstrap, service runner, USB report loop and ABI probe are work in progress. There is no Android image builder or flashable image 30. Do not deploy these scripts directly.

The ABI probe source was extended after its last successful compile: its existing local binary is stale. Rebuild into a fresh destination and update its manifest before use. The added block checks open fixed device paths for write access without truncation or writing, then close them; raw-ioctl checks pass invalid NULL payloads, never valid commands. They have not run on hardware.

The proposed first startup uses the installed Android 4.4 system read-only with journal replay disabled, fresh RAM-backed data/cache, and approved software graphics/default HALs in RAM overlays. The system hash manifest, transformed init configuration, original-init rename/symlink handling and report-parser support are not implemented. The bootstrap currently references missing generated files and must fail closed.

Next work:

1. Finish an offline image builder that preserves the original ramdisk separately, renames the original init and retargets ueventd/watchdogd correctly; omit legacy USB/modem/recovery-writing services and unintended imports.
2. Add explicit read-only Android mount/report validation while retaining the stricter existing diagnostic mode.
3. Rebuild and verify the final ABI probe, test the generated startup files and mounts offline, and audit the assembled boot image.
4. Only then perform a boot-partition test with the preserved original available for restoration; collect bounded init, service and Android logger reports.

Software EGL/OpenGL ES 1 fallback is a proposal based on AOSP 4.4 source. The installed custom ROM's behavior is not proven. Its runtime libraries advertise some NEON attributes despite the working Tegra 2 ROM; this does not establish whether the newly exercised paths are compatible. Touch, Android framework startup and a lockscreen remain unverified. No reliable completion date is established.

Work is checkpointed to conserve the user's remaining credits. No build, flash, device watcher or background development task is intentionally left running.
