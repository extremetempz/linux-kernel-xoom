# Image 32: isolated factory touch bring-up

23 October 2026. Built and audited locally; no physical result is claimed here.
Image 31 remains the hardware-tested Android 4.4.4 Welcome-screen control.

- Kernel source: `fd24d166a00bd9860f1a287b9b974843bddcc716`.
- Separate patches: `0056` initialization failures, `0057` factory policy and
  error/IRQ cleanup, `0058` isolated P3 touch configuration/device tree.
- Kernel release: `4.4.147-wingray-android44-touch`; cookie `0x584d0020`.
- Image SHA-256: `2793ccb4e30f5fe65b20a868da2a7861f5058ef233792f1cac62584eae014f69`.
- Expanded configuration SHA-256:
  `ce92df8d4e7e18bc727eb8e8130bf6d9a3a977814c55e28dda7b9c3ae1cf91b1`.
- Full kernel build, compiled-DT/expanded-config checks, driver fault tests,
  native observer tests and seven shell-report tests pass. The complete
  adversarial touch report is 21,407 bytes, below its 24 KiB budget.
- Static ARM ABI/display/touch tools have no NEON, dynamic dependencies or
  undefined symbols. Image header, decompression ranges and appended DTB audit
  pass. The source snapshot and original images remain local and private.

## Scope and evidence

The working kernel's P3 board source and saved working-ROM GPIO capture identify
I2C0 address `0x5b`, PV2/GPIO170 low-level interrupt, PJ2/GPIO74 active-low wake,
and PR4/GPIO140 active-low reset. Reset is asserted for 10 ms, followed by a
100 ms settling interval. The existing shared panel supply is retained. The
new device tree adds only these touch pins and this I2C child to the tested
Android display tree; it does not enable the broad peripheral tree.

The existing generic `atmel_mxt_ts` driver already implements Wingray's power,
reset and factory T9 configuration path. Reuse that implementation. Separate
corrections propagate initialization failures and restrict firmware/configuration
programming for the Wingray compatible. Normal volatile power/calibration is
permitted; uploading firmware, replacing configuration or backing it up to
controller NVRAM is outside this experiment.

The dedicated `android44-touch` profile enables input, evdev and this driver.
The tested `android44` and `display` configurations are preserved. SMP, PL310,
CPU frequency/idle/suspend, PMIC drivers, GPU engines and other input drivers
remain disabled. A distinct release and trace cookie identify the experiment.

## Checks before a device test

1. Run fault-oriented tests for the driver's Wingray initialization and
   programming restrictions. Compile the device trees and validate GPIOs,
   interrupts, pin-group capabilities and unchanged control configuration.
2. Build the full ARM kernel using the pinned compiler. Verify the actual
   expanded configuration, symbols, appended DTB and retained memory/storage/
   display/USB gates.
3. Build the ABI observer and read-only touch observer for the exact kernel
   release and configuration. Require static ARM code without NEON or dynamic
   dependencies; bind the packaged binaries to source/configuration hashes.
4. Package a new boot image without overwriting earlier images or evidence.
   Audit its Android header, load addresses, ramdisk and storage policy.
5. Verify wall power, device identity and both complete original boot/recovery
   partitions before a boot-partition-only test. Retain the original restoration
   image and manual fastboot recovery path.

## Physical acceptance

The USB report uses the existing fresh, nonce-bound framing and read-only
storage checks. An independent evdev observer opens only the named maXTouch
device read-only for five seconds. It does not grab input from Android, inject
events, access raw I2C or change controller settings. It records bounded
identity/capability/range information and contact transitions, and compares IRQ
counters before and after the sample.

Require real press, movement and release events, sensible coordinate ranges,
no dropped-event indication, and visible Android UI response. Test edges and
orientation, then two simultaneous contacts and release. A bound driver,
an event node or a passing host test alone cannot establish touch response.
An incomplete sample or an operator observation without corroborating events
must be recorded as such.

Restore the original boot image after the test and verify both complete
original images again. No recovery, partition table, original userdata/cache
or controller NVRAM writes are part of this stage.

## Following stage requested by the user

After physical touch response is established, audit Decatf's p4wifi kernel and
Android repositories against this port and the original working Wingray kernel.
Cover SMP, PL310, CPU frequency/voltage, nvhost/nvmap, EGL/gralloc/composer and
Android 4.4 kernel interfaces. Classify reusable code by its actual ABI and board
dependencies. Prepare separate patches and build/physical gates; do not import
Samsung regulator, pinmux, display-timing or power-control tables by inference
from the shared SoC.
