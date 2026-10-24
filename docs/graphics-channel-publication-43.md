# Graphics channel publication and work order

No device access, reboot or flash was performed. Existing hardware-tested
configurations and original images remain unchanged.

## Separate correction

Patch 0085, kernel commit `dc9bb672`, fixes the existing Decatf channel-device
registration function in `bus_client.c`. A failed `cdev_add` previously leaked
the allocated device number; a failed `device_create` also left the character
device registered. The correction unwinds only the stages which succeeded,
clears the failed node pointer and retains the original error. The device
number now uses `dev_t`, matching the registration API.

The actual function is extracted into a host fault fixture. All three failure
stages return the expected error, release their registrations, and can be
retried. Successful publication also passes. The fixture runs with undefined
behavior checks; it does not simulate live open/remove races or hardware.
The existing submission-stream regression also passes. The changed source
was copied to the existing full-graphics build mirror, compiled as
`bus_client.o`, and linked into ARM `vmlinux`. Private artifact directory
`artifacts/graphics-channel-publication43` records the source revision, hashes,
configuration and compile-only limits. No boot image was packaged.

This correction does **not** fix the later `nvhost_client_device_init` failure
path: it still publishes the user device before module initialization and has
incomplete cleanup on a subsequent failure. That remains a separate change,
requiring channel/context teardown review before reordering publication.

## Confirmed remaining source gaps

In `nvhost_acm.c`, `to_state_running_locked` ignores EMC rounding/rate-setting
failures. A failed later clock enable returns without unwinding earlier enables
or the parent busy reference. The function and `nvhost_module_busy` have void
interfaces. Host IRQ activation errors are logged through a void callback;
logging alone cannot veto downstream command submission. These are verified
source properties, not a diagnosis of a physical graphics failure: this full
legacy engine profile has not been tested on the Xoom.

The next coordinated patch must propagate readiness errors from parent/engine
power-up through submission, balance clock/reference failures, and prevent
command publication when activation fails. It must preserve idle/error paths
and be tested with failed EMC votes, each failed clock, failed IRQ activation
and repeated recovery. Reset and powergate callbacks need the same ownership
review; a local return-value change alone is insufficient.

## Agreed order and completion gates

Wi-Fi, Bluetooth and charging development is queued **after** these six areas.
Initial smoke passes are preserved, rather than treated as full completion.

| Area | Current evidence | Gate before calling it complete |
|---|---|---|
| Tegra 2 SMP | Two-core Android boots with and without trace | Repeatable boots, concurrent load and applicable lifecycle checks |
| PL310 | Initial UP/SMP boots and memory checks | Cache/RAM pressure and sustained cross-core checks |
| Frequency and voltage | Prerequisite source corrections; scaling disabled | Motorola OPP/rail/EMC validation and measured safe transitions with failure veto |
| nvhost/nvmap | Physical allocator and cached two-client sharing passes; host setup corrections compile | Validated Motorola resources, runtime activation, submission/completion, DMA coherency and lifetime tests |
| EGL/gralloc/HWC | Software Android boot; original-kernel NVIDIA offscreen probe passes | Same probe renders correctly on Linux 4.4, then accelerated posting/composition and synchronization checks |
| Android 4.4 IPC/memory | Framework boot, basic Binder/ashmem/logger/VM checks | Expanded Binder/FD, reclaim/OOM and stability checks |

For graphics, retain separate patches and gates: client lifetime; checked
runtime activation; Motorola clock/reset/EMC resource validation; actual
installed submission dialect; isolated vendor-EGL offscreen rendering; then
framebuffer/composer synchronization. Reuse Decatf's driver and Motorola's
matched userspace. No Samsung board power, pinmux or display settings are
approved by these compile or fixture results.

**Linux 4.4 acceleration remains unproven.** No new flash is authorized by this
checkpoint. Peripheral work has not started.
