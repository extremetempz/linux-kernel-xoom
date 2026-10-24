# Offscreen rendering diagnostic 55: built-in runtime

Prepared 25 October 2026. **Rendering is enabled for this test but remains
unproven on Linux 4.4 until hardware results are captured.**

Build 54 confirmed live RAM-runtime startup and host/GR2D/GR3D publication, with
fixed low engine clocks, physical EMC reporting 600 MHz and no panic. Preserve
that startup-only image. Test 55 changes only trace identity and userspace probe
selection; no new GPU driver implementation or Samsung board settings are added.

The same original-ROM NVIDIA EGL libraries and SHA-pinned two-frame probe are
embedded in the kernel via existing Linux initramfs support. The probe already
rendered two distinct frames on the working 2.6.39 kernel. It checks NVIDIA
identity and pixel readback; it is not a replay of raw decoded submissions.

Original Android init supplies the property workspace. Only a disposable child
receives `LD_PRELOAD` and the explicit probe opt-in; PID1 and the USB reporter
remain unpreloaded. The child has the existing 20-second alarm and an independent
35-second kill timeout. Reports include probe output, before/after interrupts and
clock state. Reporting starts independently of the child. There is no Android
framework/display startup, persistent storage mount, CPU DVFS/voltage or DRAM-rate
change. This tests offscreen rendering, not visible Android acceleration or HWC.

The tiny external archive remains empty; built-in runtime avoids dependence on
its known failing input path. External-initrd corruption remains unresolved.

Image SHA256: `63d23f6b9f37d6b4400c7283007f5619ed312fbce41f18aea95d9517eedea00b`; 5797888 bytes. Fresh cookie `0x584d0055`;
source commit `a81ed5db`, patch 0105. Build/source/image checks passed, including
exact ELF-linked builtin data/size, compressed Image identity, conservative
16-MiB footprint bound, ARM reset emulation, unchanged board DT, runtime dependency
closure, child-only preload, timeout and no-block-mount gates. Thirteen host probe
success/failure cases, constructor isolation, submission-trace parsing and actual
client-reset rollback fixtures passed. None substitutes for Tegra job execution.

Fresh original-image/power checks, boot-only test, original restoration and
complete original partition readback remain required. Accept acceleration only
with the intended NVIDIA identity, two correct distinct readbacks and supporting
engine activity; publication or initialization alone is insufficient.
