# Image 37: isolated CPU1 startup trace

**Hardware update:** the [completed test](trace-boot-attempt-37.md) confirms
both CPUs online and Android boot completion. Original images are restored
and verified. The design and pre-test validation record follows.

24 October 2026. Image 35 boots Android with SMP enabled and only CPU0 online.
Image 36 with both CPUs allowed remained at the Motorola logo without USB
reports. The CPU1 stopping point is unknown; this patch instruments it rather
than asserting a cause or substituting an untested reset sequence.

## Implementation and boundaries

Kernel commit `b6483deb`, exported as patch 0070, adds a default-off
`MOTOROLA_XOOM_SMP_TRACE` option and a separate `android44-smptrace` profile.
The tested configurations are unchanged. This does not enable the UP tracer.
DT wiring/resources match the tested P3 tree apart from the model string.
CPU frequency/voltage changes, hotplug, idle, suspend and legacy GPU stay off.

The first 128 bytes of the existing reserved/no-map console hole at
`0x1fe00000` hold a distinct magic, version and build cookie `0x584d0037`.
CPU0 initializes the record through an uncached static mapping only after
Wingray identification. It clears old fields and publishes the header last.
CPU0, CPU1 reset assembly and CPU1 C each have a distinct progress word;
there are no shared read-modify-write updates, allocation or trace locks.

The reset handler receives the physical trace address through its copied IRAM
control data. That address stays zero on other boards; reset assembly then
performs no physical trace access. It also checks the header and CPU ID before
writing. The instrumented handler and data occupy 448 bytes of the existing
1024-byte reservation. No extra IRAM area or Samsung board state is imported.

Checkpoint groups distinguish:

1. Mapping initialization, reset-handler installation and SCU setup on CPU0.
2. CPU0 reset assertion, flow clear, clock enable, reset release and return.
3. CPU1 arrival in the IRAM reset handler, before its erratum setup.
4. CPU1 secondary C after its MM switch, CPU-starting notifications, delay
   calibration and online-completion signalling.
5. CPU0's returned startup result and observed online state after waiting.

Missing or stale records do not prove a location was never reached: reset
retention, bootloader activity and trace writes/barriers can affect evidence.
The build cookie is not a unique boot nonce. Preserve attempt provenance and
use a fresh cookie for a repeat experiment. The trace changes timing and does
not test sustained coherency, interrupt delivery or memory-pressure stability.

## Offline checks completed

- Full ARM kernel link, appended DTB, resolved configuration and source/DT
  isolation checks; rejected wrong cookie, disabled trace and unsafe profiles.
- Actual linked reset instructions under Cortex-A9 emulation: valid CPU1
  writes only its assigned word; disabled board, CPU0, wrong magic/version/
  cookie write nothing. Scratch-register boundaries are checked. Unicorn's
  read-only MPIDR model is replaced with the selected CPU-ID input only.
- Actual C helper tested with substituted MMIO/barrier providers: not-ready,
  bad headers and every invalid offset are rejected. These providers do not
  emulate real cache/barrier behavior.
- Exact-release static ARM Android ABI, touch and two-CPU memory probes rebuilt.
  Bootstrap, read-only storage/report protocol, SoC and touch report regressions
  pass. Image headers, load addresses, decompression and appended DTB audited.

Prepared boot image SHA-256:
`b2a3d0ef172c4e1692701b6fa5aee70de36d44bedb1c5888a6b4adda3ed9aa59`.
This is preparation evidence, not a hardware boot result.

## Hardware sequence

1. Confirm original Android/root/boot completion, battery, memory ownership,
   exact candidate hash and full boot/recovery partition hashes. The small
   hash responses avoid the bulk ADB transfer stalls observed after image 36.
2. Flash boot only, observe for two minutes, and collect a fresh USB report if
   available. Screen content alone cannot establish CPU1 online state.
3. Restore the verified original boot, return to Android, and verify both
   complete original partition hashes again. Recovery/layout remain untouched.
4. Recheck the original memory map. Use the existing hash-pinned, bounded,
   read-only mmap snapshot reader once, with no direct /dev/mem read fallback.
   Clean up its unique temporary deployment and check original Android remains
   running. Decode only matching magic/version/cookie; reject unrelated data.
5. Use the last independently recorded CPU0/reset/C checkpoints to choose one
   next experiment. Do not introduce graphics or DVFS changes into this test.

This advances the SMP/PL310 track. DVFS still requires the installed DRAM revision
and Motorola rail/EMC sequencing. Legacy nvhost/nvmap, original HWC0/gralloc/EGL
and asynchronous synchronization still require their separate validation stages.
Android Binder/ashmem/logger basics remain demonstrated, with broader transaction,
reclaim/OOM and endurance coverage pending.
