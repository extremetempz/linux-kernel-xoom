# Wingray early RAM trace build — 2026-10-18

Linux 4.4.147 now has an optional, compiled RAM trace profile. This is an
instrumentation proposal, not a verified fix for the Motorola-logo failure.
Source commit: `361622c8`, carried separately as patch `0005` after the existing
four patches. The peripheral port and its prior failed image were preserved.

## Verified offline

- `trace` and uninstrumented `early` profiles both compile with the pinned GCC
  4.9 toolchain and pass the ARM/DTB/memory/profile verifier.
- Both profiles use the same early DTB, SHA256
  `ab186459f800c309124302757b2e883f757d80d3cf8d2314869fa7890fc18949`.
- Trace `zImage-dtb`: SHA256
  `fdf063ee12578bebc34ff91a532859a1136a02f6676bb0309c8ca8e165a51e37`.
- Control `zImage-dtb`: SHA256
  `caad963562ffbf9c33dd6ca49cb24c8ad77246a64d40db3fbbf99f2b16fc4b4c`.
- Actual compiled zImage-entry, ATAG-return, kernel-entry and pre-MMU snippets
  passed 16 NZCV flag patterns each under Unicorn's Cortex-A9 model: 64 runs.
  Boot argument registers, stack pointer and flags were preserved; writes stayed
  within the first 128 bytes of the trace reservation. These are snippet tests,
  not full boot, cache-coherency or reset-retention tests.
- The offline decoder accepted a valid synthetic record and rejected a wrong
  cookie and invalid magic. Shell and Python syntax checks passed.
- Original boot and recovery backup checksums still match. No device image was
  flashed, partitioned or overwritten during this build continuation.

Local outputs are in `artifacts/boottrace-build-1` and
`artifacts/boottrace-control-build-1`. Neither output is a packaged Android boot
image. Build logs and compiler intermediates remain in `/tmp/xoom-trace-build`
and `/tmp/xoom-trace-control` (logs have `.log` suffix).

## Instrumentation

The dedicated UP ARM profile disables pre-console UART polling, SMP, the L2
driver and peripheral probes. `CONFIG_MOTOROLA_XOOM_BOOT_TRACE` defaults off.
It uses physical `0x1fe00000..0x1fe0007f` inside the already reserved 2 MiB legacy
console hole, below the upper 1 MiB Android RAM console/ramoops region. This
choice is a candidate software reservation; bootloader ownership and persistence
across reset are not established.

The zImage entry clears the 128-byte record and captures r0/r1/r2, entry PC and
CPSR. Subsequent stores record SCTLR/CPUID, CPU-mode normalization, ATAG-to-FDT
return status and FDT pointer, before/after decompression, `stext`, before MMU
enable, Tegra `init_early`, and an early initcall. Pre-MMU stores use cache-line
clean operations and barriers. They assume the ARM boot protocol's privileged,
MMU-off entry state. UART polling is unnecessary for these stores, but the RAM
address or cache operation could itself introduce a hardware-specific failure.

Record magic is `0x584f4f4d`, format 1, default build cookie `0x584d0001`.
A matching cookie identifies a build, not a unique attempt. An absent or stale
record cannot prove the bootloader never entered the kernel. No marker proves
its succeeding stage completed. The decoder only reads a supplied host file.

## Confirmed preflight failure — hardware tracing blocked

A read-only `/dev/mem` preflight against the working 2.6.39.4 kernel returned no
data and caused that kernel to panic. The retained `/proc/last_kmsg` identifies
a paging fault at virtual `0xdfe00000`, with PC in `memcpy`, followed by a fatal
exception. That virtual address corresponds to the attempted physical
`0x1fe00000` direct-map read. The legacy kernel removes this RAM hole from its
ordinary memory mapping: physical RAM existence did not make this access safe.
The prototype device reader was deleted and is not included in the patch series.
The private retained log remains local; it is not uploaded.

The user confirmed the working Android ROM returned. No further physical-memory
read was attempted. The unsafe read was a failure of this preflight method,
not evidence about execution of the new kernel, which was not booted this turn.

## Staged validation plan

1. Review a safe observation method first. Options include a verified recovery
   mapping implementation or physical UART with bounded polling. A new mmap
   reader is only a hypothesis and must not be tried as a substitute without
   reviewing the old kernel's mapping code. Establish reset retention, trace
   address ownership and a way to distinguish stale records before interpreting
   physical markers. Hardware validation is blocked at this stage.
2. Only after that review, prepare a separate boot image with the verified
   original header/load addresses and ramdisk. Audit appended-DTB boundaries,
   decompression destination and image size again; preserve every original and
   prior candidate. Obtain explicit approval before any boot-partition write.
3. If approved, test the minimal early profile and trace variant in controlled
   attempts, collect the earliest surviving marker, then restore and verify the
   original boot partition. A logo or missing USB enumeration alone cannot
   locate the failing stage. Fastboot RAM boot remains forbidden by this device.
4. After C initialization is established, add a minimal USB/initramfs console,
   then interrupt/timer stability, SMP/L2, storage reads, display, touch, Wi-Fi,
   suspend/resume and remaining peripherals one subsystem at a time. Keep ROM
   integration deferred until repeatable kernel boot and recovery are established.

Reproduce offline checks after fetching the pinned donor and applying patches:

```sh
XOOM_PROFILE=trace bash scripts/build-wingray.sh
XOOM_PROFILE=early bash scripts/build-wingray.sh
bash scripts/setup-trace-tests.sh
PYTHONPATH=toolchains/trace-test/site-packages python3 tests/test-boottrace-arm.py /tmp/xoom-trace-build
```

For the last command, substitute the trace build directory printed by the build
script. The test dependency is a SHA256-pinned Unicorn 2.1.4 wheel for Linux
x86-64, installed inside this workspace only.
