# Image 33: touch startup IRQ correction

23 October 2026. Two fresh nonce-bound, SHA-verified USB reports confirm
Android 4.4.4 boot completion, working touch events, full eMMC capacity and all
ten BigPart extents on Linux 4.4.147. This is a UP/software-graphics control,
not a test of CPU1, enabled L2, DVFS or NVIDIA GPU acceleration.

Image SHA256: `58fb8c305dc3757772afd26e0b03d6024c55b8e77397439dbe7ef4b5bb9639a1`.
Kernel commit: `159616f7936b918918066b416140d03008a3526d` (patch 0059).
The tested touch configuration and board wiring are unchanged from image 32.
A bounded read-only CPU/cache/memory observer is included explicitly.

## Physical evidence

| Five-second sample | Events | New presses | Releases of observed contacts | Touch IRQ before/after | Invalid events |
|---|---:|---:|---:|---|---:|
| 1 | 13 | 1 | 1 | 124 / 126 | 0 |
| 2 | 310 | 6 | 4 | 402 / 503 | 0 |

Sample 2 sees two simultaneous new tracking IDs and their releases; two new
contacts are active when sampling ends. Two additional release records concern
contacts already down before recording, so are not counted as releases of
observed presses. Both samples finish normally with no tracking-ID replacements
or suppressed contact records. The observer does not grab or inject touch.

Both reports contain `sys.boot_completed=1` and `dev.bootcomplete=1`. The native
ABI/storage guards pass. Disk capacity is 62,521,344 sectors; all ten extents
match the original reference. Original userdata/cache are not mounted; system
is read-only with journal replay disabled, and Android data/cache use RAM.

Image 32 had a cumulative touch IRQ count of 213,838 before its first sample
and logged RT throttling at startup. Image 33 has 124 before its first sample
and neither captured boot log contains that warning. The result supports the
request-masked IRQ correction and shows no comparable startup burst in this
boot. It is not an endurance or suspend/resume result.

| Capture | Bytes | SHA256 |
|---|---:|---|
| 1 | 113102 | `d467731149f2768728fbc3a4ee8d457fbfcfcec4fbb42c2f63b67c277726696d` |
| 2 | 117688 | `19994a6aa60564d90610c2d30840c532bafe01e2c8e2455c69f98934e1635405` |

Raw reports and device identities remain private.

## Read-only SoC metadata

The kernel reports Tegra SoC ID 32, revision 5, and ARM CPU ID `411fc090`
(Cortex-A9, variant 1, revision 0). CPU possible/present/online masks each
contain only CPU0, as expected for this UP configuration. This does not test
CPU1 or prove whether the firmware left any secondary hardware powered.

Clock-framework metadata reports cclk/PLL-X at 1 GHz, PLL-P at 216 MHz and
EMC at 600 MHz. These are reported framework rates, not independent electrical
measurements. `MemTotal` is 738672 kB under this reserved-memory configuration.
CPU-frequency and cache sysfs attributes are unavailable; that absence alone
does not establish physical cache state or installed memory part identity.

## Android userspace limitations

The second report contains two `com.android.wallpaper` SIGSEGV tombstones
inside `strcmp`, called from `RsdShaderCache::vtxAttribSlot` in
`libRSDriver.so`. It also records a Google Play services persistent-process ANR
and substantial software SurfaceFlinger CPU usage. These are real unresolved
userspace failures; boot completion does not establish a stable complete ROM.
The captured stacks locate failures but do not prove their root causes. Do not
attribute them to Binder, L2, SMP or the IRQ correction without reproduction
and controlled comparison. Preserve software graphics while investigating
the RenderScript/GLES boundary and first-boot service load separately.

## Restoration and remaining limits

Original boot was restored. Full fresh boot and recovery readbacks match
the preserved originals; the working Android ROM completed startup and kept
the same boot ID throughout verification. Recovery and partition layout were
not written. No restoration is pending.

Image 32 already had operator-confirmed Welcome/touch response. This image's
reports independently establish Android completion and touch events; explicit
operator confirmation of edge alignment and a visible lockscreen remains
outstanding. See [staged implementation progress](decatf-implementation-progress.md)
for the separately compiled PL310/SMP profiles and limited driver corrections.
