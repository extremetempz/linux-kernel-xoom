# Trace 50: root-mount panic and EMC vote-clock rejection

Findings committed 25 October 2026; the hardware test and readback occurred
24 October. **The retained trace identifies the boot-stopping panic before
userspace. GPU rendering was disabled and remains unproven.**

## Verified evidence

The one guarded 128-byte snapshot has the expected cookie `0x584d0050`, SHA256
`5c738a9045564375c68f7244815fb28ca03d7e2642b1d06e63613602e4b6d039`.
Its matched `System.map` SHA256 is
`6cd6e14acfb118052dc8e582f157085cdf1caad94d90433e5691dfe6c9bf9863`.

- The panic notifier retained **`VFS: Unable to mount`**. This matches the
  root-filesystem panic sites in `init/do_mounts.c`; the record stores only the
  first 20 bytes, so the full message and target device were not recovered.
- Kernel stage 4 remains set, with no userspace/reporter markers. The final
  recorded PID1 initcall, `clk_disable_unused`, returned 0. It was not recorded
  as stuck inside that function.
- CPU1 startup result is 0 and its online bit is 1. Host stage 61/result 0
  records successful host initialization/publication.
- GR3D stage **`0x115`**, result `-22`, identifies clock index 1, event 5.
  GR2D stage **`0x125`**, result `-22`, identifies clock index 2, event 5.
  Both indexes name **`emc`** in the Tegra 2 device clock lists. Event 5 means
  the old CCF-reported rate was zero despite a positive rounded requested rate;
  the guard returned `-EINVAL`. These are clock-validation failures before the
  initialization setter loop, not GPU job/submission failures.
- USB composite registration returned 0, but no diagnostic USB device appeared
  in the guest and no reporter startup marker was recorded.

## Interpretation and remaining unknowns

The immediate boot stop is a root-mount panic, before the RAM diagnostic could
execute. The trace does **not** prove why the initramfs `/init` was unavailable
or whether the bootloader supplied the complete intended ramdisk. The source
falls back to `prepare_namespace()` when the early init path is inaccessible;
that is a relevant path to investigate, not a verified ramdisk/bootloader cause.

The zero-rate EMC vote-clock rejection is a separate, precisely located engine
bring-up blocker. Its underlying CCF registration/rate-reporting cause still
needs validation. Nothing here proves that it caused the VFS panic. Do not
bypass the clock guard, change DRAM rates or import Samsung power tables based
on this result.

Next work should inspect the bootloader/initrd handoff and kernel unpack/access
of `/init`, then validate why the diagnostic software EMC clocks report an old
rate of zero. Preserve separate patches and retry startup before rendering.
No functional correction or further build/flash was made during this wrap-up.

## Device preservation

Original boot restoration and reboot succeeded. Android returned on ADB after
the startup interval. Complete boot (8 MiB) and recovery (12 MiB) hashes match
the original backups; recovery and partition layout were not written.
No restoration remains pending.

The existing SHA-pinned reader took one stable read-only snapshot after fresh
original-ROM, full-image-hash, memory-map and build-artifact checks. Its temporary
copy was kept in `/dev` RAM and removed. Android remained boot-complete with
unchanged boot ID and no newly detected fault in the before/after kernel-log
comparison. Private evidence is in `artifacts/gpu-startup50-attempt1/`; raw logs,
device identifiers, original images and NVIDIA runtime files are not committed.
