# Image 32: Android Welcome with working touch

23 October 2026. **Physical result:** Android 4.4.4 completes boot on Linux
4.4.147, displays Welcome, and responds to touch. The operator confirmed UI
response. Independent read-only evdev samples verify presses, movement, explicit
releases and two simultaneously active contacts.

Image SHA-256: `2793ccb4e30f5fe65b20a868da2a7861f5058ef233792f1cac62584eae014f69`.
Kernel source: `fd24d166a00bd9860f1a287b9b974843bddcc716`; release
`4.4.147-wingray-android44-touch`, cookie `0x584d0020`.
See [preparation and build checks](trace-boot-attempt-32-prepared.md).

## Verified hardware results

The generic maXTouch driver binds I2C0 address `0x5b` and registers
`/dev/input/event0` as **Atmel maXTouch Touchscreen**, with direct-input property,
16 slots, X range 0–2580 and Y range 0–1630. Factory identity is family 160,
variant 0, firmware 1.0.FF, matching the previously captured 0x10FF identity.
The profile performs no firmware/configuration programming.

Three fresh nonce-bound, SHA-verified reports retain both Android boot-completion
flags, the native ABI gate, USB, full 62,521,344-sector capacity and all ten
BigPart extents. Software read-only eMMC, `ro,noload` system, RAM-data/cache and
RAM-only HAL/GLES overlays remain verified.

| Five-second sample | Events | New presses | Explicit releases | Positions | GPIO170 IRQ increase | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| 1 | 230 | 4 | 4 | 62 | 42 | Complete single-contact transitions and movement |
| 2 | 2,233 | 0 | 0 | 803 | 272 | Two slots moving, already held at start; not proof of new tracking IDs |
| 3 | 520 | 7 | 5 | 37 | 172 | Two simultaneous new tracking IDs and subsequent releases; two contacts remain down at end |

All samples have zero invalid events, no tracking-ID replacements and
`deadline_complete`/exit 0. No `SYN_DROPPED` or event-cap failure occurred. Sample 2
suppressed 453 printed coordinate records at the output limit; counting continued.
Samples 1 and 3 printed every contact record. The observer never grabs input
from Android or injects events.

| Capture | Bytes | SHA-256 |
|---|---:|---|
| 1 | 113,901 | `285aa6880149e76b1f1a96e0596a95ae3aecff7e3c96ee71ce628b02a2908c02` |
| 2 | 110,641 | `4594b803a9ea08885e077f696d7b839cada0b1f065344503e061f3fde4a0b334` |
| 3 | 107,183 | `6c9619e559cfefcbe49c04d6a5b8be6bdfccc5f43777ec3aebeb96f5e39a8462` |

Raw reports and copied ROM files remain private and excluded from Git.

## Startup interrupt burst and separate fix

The kernel logs `sched: RT throttling activated` at 1.967 seconds and names the
touch IRQ thread as a potential CPU hog. Its cumulative IRQ count reaches
213,838 before sample 1. Image 31 lacks this warning. These facts establish a
startup burst; the sample deltas do not indicate an ongoing storm during the
observations.

There is a concrete source race: `request_threaded_irq` unmasks the low-level
interrupt before returning. A subsequent mask cannot prevent the higher-priority
handler from running first. Before the object table exists, the handler returns
without draining the controller. This is a well-supported explanation of the
burst, **not proven attribution**.

Separate patch `0059`, commit `159616f7`, requests Wingray's IRQ using
`IRQ_NOAUTOEN` and enables it after object setup. Its regression test simulates
preemption inside the IRQ request and rejects the old behavior. It preserves
the tested configuration/DT. The candidate-33 kernel build passes; it was not
flashed. Physical removal of the burst remains a future test gate. Image 32 and
its source snapshot are preserved.

## Restoration and limits

Original boot was restored. Complete fresh boot and recovery readbacks match
their preserved originals; original Android reports boot completion and retained
the same boot ID during verification. Recovery and partition layout were never
written. Original userdata/cache were not mounted by this experiment.

Basic touch and two-contact tracking are demonstrated. All-edge calibration,
orientation under rotation, endurance and suspend/resume remain unvalidated.
The operator did not explicitly confirm the requested edge-alignment check.
Welcome is verified; a lockscreen remains unverified. The experiment uses
software graphics, one CPU and firmware-initialized power rails. It does not
establish GPU acceleration, PL310, DVFS or charging.
