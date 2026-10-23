# Motorola resource and framebuffer compatibility changes

The subsequent [Motorola resource profile](wingray-legacy-resource-profile.md)
is now implemented and compiled for the allocator-only stage. It remains
hardware-untested; this document records the preceding compatibility checkpoint.

24 October 2026. **Code changes were required and have been made. No device
was rebooted or flashed.** This is an offline checkpoint, not boot attempt 42.
The latest source is `8ff68875`; the hardware-tested configurations/device trees
remain unchanged. Legacy accelerated graphics is still not demonstrated.

## Implemented separately

| Patch | Source commit | Change |
|---|---|---|
| 0075 | `8d5b9e05` | Validate the complete nvmap carveout list before use; reject malformed/empty/overlapping ranges and bad allocation parameters; propagate parser errors instead of leaving zero-filled heaps. Wingray requires explicit early reserved-memory references. |
| 0076 | `4c553a04` | Restore original Motorola framebuffer declarations and add an optional synchronous linear-RGB posting path using existing nvmap/DC APIs. No board timing, regulator, pinmux or power data added. |
| 0077 | `78c4718f` | Check every covered Wingray carveout page against the actual ARM RAM map; a DT `no-map` declaration alone does not prove early removal succeeded. |
| 0078 | `8ff68875` | Stop DC and release pinned buffers before controller teardown; defer framebuffer mapping/object release to fbdev's last-reference callback. Existing open files fail further controller operations after removal. |

These are exported, independent kernel commits. The earlier
[Decatf full-link corrections](decatf-graphics-integration.md) remain prerequisites.
The original Motorola source comparator is
[ElementalX `3cfbd6c3`](https://github.com/flar2/xoom-ElementalX/tree/3cfbd6c3fe34a9833e1a13c4a1d47c3ef58c48fd);
the existing Decatf host, allocator and controller implementations are retained.

## Resource validation: implemented scope

The old parser counted all children, silently skipped bad resources and called
`memblock_remove` while still parsing. It could return platform data containing
unused zero entries, or change memory bookkeeping before a later error.

The revised parser counts available children, bounds the list, validates all
ranges and allocation parameters, checks overlap, and balances OF references
on success/error paths. On Wingray each entry must supply one `memory-region`
phandle to an available direct child of `/reserved-memory`, with static `reg`,
`no-map`, no `reusable` flag and sufficient extent. Every covered page must be
absent from `pfn_valid()`; this ARM configuration implements that lookup using
the retained memblock memory map. Wingray never relies on late probe-time
memory removal. The pre-existing non-Wingray binding remains available after
the complete list passes validation.

This validates **allocator backing ownership**, not the correctness of a new
Wingray graphics layout. It does not decide which IRAM areas belong to the CPU
reset handler, AVP/resume code or graphics, nor whether two separate devices
reference the same reservation. It does not validate GART, engine clocks,
resets or board power. No legacy nvmap/device-tree resources have been enabled.
In particular, do not import Samsung's IRAM or graphics reservations as a way
to satisfy this guard. The already tested Motorola video reservation is intact.

## Framebuffer compatibility: implemented scope

`CONFIG_FB_TEGRA_WINGRAY_LEGACY` defaults off. It requires built-in legacy
framebuffer/DC/nvhost/nvmap and excludes the competing display-extension,
overlay and framebuffer-console clients. Runtime activation is restricted to
`motorola,wingray`. A missing nvmap provider defers the DC probe before power-up.

The original `SET_NVMAP_FD` and 260-byte `FLIP` requests now have handlers.
The ARM32 request numbers, structure sizes and member offsets match the pinned
Motorola headers. The path reuses the original authorize/duplicate/pin sequence,
adapts integer coordinates to Decatf's fixed-point window representation, and
uses Decatf's existing window update, wait and syncpoint operations.

Initial supported scope is deliberately explicit:

- Up to three windows; `index=-1` ignores an entry and `buff_id=0` disables it.
- Six original packed RGB formats (16/32-bit), horizontal/vertical inversion,
  original blend modes and placement within the current display mode.
- Linear, unscaled surfaces only. Tiled, YUV/planar, unknown flags and scaling
  return errors. They are not silently reinterpreted.
- Full crop/stride/offset and pinned-allocation extent validation, including
  arithmetic and 32-bit display-address limits.
- Exclusive framebuffer ownership and stable imported references. Closing a
  userspace client retains its current front buffer until replacement/removal.

Posting is **synchronous** in this first compatibility path. Producer syncpoint
waits must succeed before changing windows. The ioctl then waits for Decatf's
scanout-completion condition before publishing a completed post-syncpoint and
releasing the previous front buffers. It does not implement the original work
queue or claim equivalent throughput/asynchronous behavior.

If scanout times out or is interrupted, both old/new buffers stay pinned, no
successful completion is returned, and further legacy flips are rejected.
Driver teardown disables DC before releasing these references. fbdev's final
file-reference callback releases the framebuffer object/mapping, so a file
that remains open during driver removal does not immediately lose its `par`.
The compatibility option remains off in all tested profiles.

## Checks completed

- Full ARM `vmlinux` links at `8ff68875`, with the compatibility option both on
  and off. Saved artifacts/configs/maps/hashes are under private
  `artifacts/graphics-compat-42-on/` and `-off/`. No boot image was made.
- Actual Kconfig resolution excludes the new option when display extensions,
  overlay or framebuffer console is selected. The console test also enables
  its VT parent, so it tests a real conflict. The existing modern-MC exclusion
  also passed in the fresh legacy build.
- Actual nvmap parser host tests cover reservation references, live RAM pages
  at the start/interior/end of a proposed range, invalid/overlapping resources,
  disabled children, allocation failures, error propagation and OF lifetimes.
- Actual framebuffer compatibility host tests cover three-window posting,
  replacement/disable/ignore behavior, all six supported formats and boundaries,
  pin/duplicate/allocation/wait failures, interrupted/timed-out scanout,
  completion ordering, client replacement, copy faults, retained pins and
  teardown with an open file. ASan/UBSan run; LeakSanitizer is disabled because
  it cannot attach in this runner. Fixtures explicitly check reference/pin
  cleanup. Providers are stubs, not physical devices or concurrency proofs.
- Compiled ARM32 framebuffer declarations match Motorola's request encodings,
  sizes and member offsets. This does not establish semantic or binary-library
  compatibility. The audit now distinguishes the unchanged donor declarations
  from the current port's added declarations.
- Exported patches reconstruct the exact source tree; tested defconfigs and
  device trees are unchanged. No Samsung board settings were copied.

Reproduce the offline checks with local sources/toolchain already present:

```sh
python3 tests/test-nvmap-dt-resources.py
python3 tests/test-wingray-fb-legacy.py
python3 scripts/audit-tegra-fb-abi.py --save-dir artifacts/new-fb-abi
XOOM_GRAPHICS_LEGACY_FB=1 \
  XOOM_GRAPHICS_ARTIFACT_DIR="$PWD/artifacts/new-legacy-fb-on" \
  bash scripts/check-decatf-graphics-build.sh
```

Use a new directory per run. Set `XOOM_GRAPHICS_LEGACY_FB=0` for the separate
disabled control. The builder does not package or flash an Android image.

## Why this checkpoint is not flashed

These changes fix concrete source/interface problems; they do not supply the
missing Motorola legacy DT/resource profile or a matched accelerated Android
overlay. Flashing this compile-only configuration would not test the intended
path: its original DT still describes the tested modern/software display,
while this alternate build selects legacy drivers instead.

Next, prepare a separate Motorola resource profile from the original source
and saved original hardware map, preserving CPU-reset/IRAM ownership and the
tested AUO/LP8550 sequence. Keep unvalidated engines disabled initially. Collect
allocator/resource reports in a boot-only diagnostic, restore/verify originals,
then test the matched NVIDIA userspace and offscreen probe. Confirm actual
gralloc layouts and scanout completion before relying on the initial RGB path;
unsupported tiled/scaled requests may be a further compatibility requirement.
The controller's `no_vsync` bypass must remain disabled for completion tests.

No recovery, partition, Android filesystem or original-image change occurred.
