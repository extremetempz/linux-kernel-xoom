# Tegra 2 implementation progress

23 October 2026. Preserve the physically tested image-32 control. Image 33
is a boot-only IRQ-startup control test; its physical result is recorded separately.
The following CPU/cache profiles are offline build products, not deployable
Android boot images. They have not passed physical tests.

## Separate changes and evidence

| Change | Source commit / patch | Verified scope | Remaining gate |
|---|---|---|---|
| UP PL310 control | `0db3935f`, kernel patch 0060 | Full ARM kernel link; existing Wingray DT properties unchanged except model; L2 latency values checked | Dedicated guarded runtime packaging, cache state/logs, RAM integrity and repeated Android tests |
| SMP control | `3a12d776`, kernel patch 0061 | Full ARM link; two possible CPUs, `maxcpus=1`, UP-only tracer disabled; registered Tegra secondary dispatcher linked | Safe observation without the UP tracer, then one-CPU control before actual CPU1 bring-up |
| cpufreq resource errors | `77d1c0ed`, kernel patch 0062 | Actual driver functions pass injected allocation/clock failures; old-source negative controls fail; real ARM object compiles | Transition rollback, stock limits and Motorola regulator/installed-DRAM EMC integration; CPU_FREQ remains disabled |
| Existing Wingray HWC buffer bounds | device commit `c7b7b055`, Android patch 0001 | Actual helper and prepare/set paths pass allocation-failure and overflow tests, with old-source negative control | Full matching Android HAL build and hardware validation; this is not GPU enablement |
| CPU/cache metadata observer | `diagnostic/soc-report.sh` | Bounded read-only fixture tests; explicit packaging opt-in | Read actual fresh image-33 report; missing sysfs attributes mean unavailable evidence |

Kernel commits are separate in `sources/kernel-donor`. The Android patch is
separate in `sources/device-wingray`. All exported patches retain their source
commit identities. Existing tested touch/display configurations are unchanged.
No Samsung board regulator, pinmux, display, power or EMC tables were imported.

The CPU profile verifier rejects CPU frequency enablement, a missing L2 driver,
unsafe SMP tracing, a changed CPU count or premature two-CPU startup. It also
compares compiled device trees against the tested touch tree. The current
Android image packager deliberately accepts neither new CPU profile: kernel
link success alone does not make either profile flash-ready.

## Graphics compatibility evidence

Static inspection of the owner's preserved Motorola `libnvrm_channel.so`
(SHA256 `2656821d3ae7060876bfcf1ed4df26230d0adde44aa5db33761eef49ecc29807`)
finds `NvRmChannelSubmit` at Thumb entry 0x2210, loading a 24-byte count at
0x2232 and calling its write-all helper at 0x2240. The helper forwards the
remaining count to `write` at 0x21e0. The donor parser consumes a 16-byte header.
This establishes a concrete static mismatch for that exported submission path;
it does not establish which calls a running graphics stack will exercise or
prove the complete blob ABI. Proprietary binaries and raw disassembly remain
private and are not part of the patch set.

The ARM32 layout audit still finds matching encodings for 13 nvmap requests,
seven measured nvmap layouts and ten shared nvhost requests. Those matches do
not cancel the submission-header mismatch. Resolve that boundary before
legacy GPU submissions or importing a proprietary Galaxy Tab graphics set.

## Android core and next gates

Binder, ashmem, legacy logger and the existing memory configuration already
supported the physically observed Android Welcome screen. Preserve that
control; avoid a broad core backport without a demonstrated incompatibility.
A visible lockscreen and persistent user installation remain separate goals.

Next: complete image-33 touch/IRQ and metadata capture, restore and verify both
original images, then add guarded PL310 runtime checks. Keep CPU1, DVFS and GPU
experiments separate. Hardware results must name the tested image rather than
infer success from the host tests or shared Tegra 2 chipset.

## Subsequent development checkpoint

See [power, graphics and ABI implementation](power-graphics-abi-stage.md) for
separate nvhost, EMC, voltage-unit, frequency-policy and composer corrections,
expanded ashmem checks, ARM build evidence and remaining hardware gates.
The earlier audit describes its pinned review snapshot.
