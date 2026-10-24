# GPU engine context and publication lifetime checkpoint

24 October 2026. No device operations, new boot image or flash in this stage.
The successful host-only hardware image, original backups and previously tested
DT/config sources are unchanged. Linux 4.4 GPU rendering remains unproven.

## Separate corrections

Patch 0093, kernel `4cbdc168`, corrects the existing Decatf T20/T30 context-save
handler allocation paths. An allocator/map failure previously leaked the
handler structure, and a failed pin was used as a physical address. Failures
now free only acquired resources, and command-save data is written only after a
successful pin. T20 also releases its temporary construction mapping, as T30
already did; later save submission uses the retained buffer and physical address,
not that construction pointer. Per-context restore mappings are unchanged.

Patch 0094, kernel `3a9d0aa2`, adds an unpublished-handler destructor which
unpins and releases the retained save buffer. Engine initialization now completes
module power/clock initialization before publishing its channel character device.
Failed module initialization destroys the allocated context handler/channel;
failed user-device publication additionally releases module attributes/clock
references. The device's channel pointer is cleared before freeing the channel.
The existing host-deferral guard is retained. No new driver was implemented.

This is specifically **unpublished initialization cleanup**. The new destructor
must not be used with open channels, live contexts, CDMA jobs or in-flight DMA.
Normal hot-remove, job teardown and restoration of an earlier physical power/rate
state are not implemented by these changes. A successful module init followed
by publication failure can leave the engine power island on with clocks gated;
software resource cleanup is not a claim of complete power-state rollback.

## Verification

Fixtures compile extracted actual T20/T30 handler functions and the common
destructor, injecting structure/buffer allocation, map and pin failures. They
check that no save data is written after failure, no pin/map/reference remains,
and successful handlers release their temporary mapping and destruct cleanly.

The engine fixture compiles the actual client initialization and channel-abort
functions. Missing host/allocator/class defer before allocation. Four failing
stages unwind the unpublished state, and successful publication requires module
readiness. It also verifies the cleared device/channel relationship.
Tests run with undefined-behavior checks and provider mocks; they do not prove
GPU command validity, cache coherence, concurrency or physical ownership.
Existing runtime activation, submit, keepalive and publication regressions pass.

A fresh full ARM vmlinux link passes with legacy linear-RGB compatibility on.
Real Kconfig negative checks reject conflicting modern memory-controller and
framebuffer owners. The expanded compile configuration is byte-identical to
`artifacts/graphics-runtime44/kernel.config`. Source files match the fresh build
mirror, and patches 0093/0094 replay exactly from `d7f39737`. Compile evidence and
hashes are in `artifacts/graphics-client47`, including the additional lifetime
verification file. There is no boot image and no hardware execution in this stage.

## Motorola resource and reset gates still open

These source/DT facts describe the donor's Tegra 2 interface; only host1x has
passed the isolated Xoom hardware test so far:

| Component | Existing Tegra 2 resources | Remaining integration |
|---|---|---|
| host1x | `0x50000000 + 0x24000`, clock/reset 28, GIC SPI 65/67 | Initial three-cycle pass at retained 150 MHz; no real GPU completion interrupt yet |
| GR3D | `0x54180000 + 0x40000`, clock/reset 24, donor requests `gr3d` and `emc` | Motorola clock/rail/powergate ownership and checked reset sequence |
| GR2D | `0x54140000 + 0x40000`, clock/reset 21, donor requests `gr2d`, `epp`, `emc` | Both engine and EPP clock dependencies; shared EMC vote integration |

The original-ROM trace confirms both GR2D and GR3D are used with the six-word
24-byte write header. It does not validate a new-kernel clock rate or DRAM table.
The legacy `emc` client clock represents a shared vote. Mapping it directly to
the physical DRAM clock in DT would bypass that aggregation and is not an
acceptable shortcut. The global donor shim also affects USB clock lookups;
its replacement/selection must preserve the working USB path and use validated
Motorola DRAM behavior, without Samsung power or timing tables.

Both engine probe routines still reset after client-device publication; GR3D
also ignores those reset results. Module-ready publication in this patch does
not close that reset window. The next coordinated patch must move checked reset
completion before publication, balance the enabled-clock interval and propagate
failure without freeing active resources. Then prepare an explicit engine/EMC
profile, validate it offline, and use the matched NVIDIA offscreen probe on Linux
4.4. Accelerated composition and completion/fence validation follow rendering.
