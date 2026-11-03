# Persistent-storage result — 3 November 2026

## Stage C second boot passed

Image:
`artifacts/storage96-stageC-postrepair-ready/wingray-android44-persistent.img`
SHA256 `15ef5b6e22724c7c0134c23344806ae7f44d4022640c2376c1e1f839a18397a4`.

Capture:
`artifacts/storage96-stageC2b`
report SHA256 `5523bae59d2bb94129b827d146bf68e4ed94f2545f0f2d7b9459f0131b92941e`.

Validated state:

```text
/data  /dev/mmcblk0p10 ext4 rw
/cache tmpfs 96MiB
p10 0
p9  1
p8  1
disk 1
```

Stages reached `persistent_data_cache_mounted`,
`ram_graphics_overlays_ready`, and `exec_original_android_init`.
SurfaceFlinger and zygote were running.

The operator confirmed Android reached the environment and that existing
apps/settings survived the reboot. The operator later confirmed additional
existing state after the persistent boot:

- apps were present and working;
- accounts were present;
- `/data/media` was present, including Photos;
- Wi-Fi configuration was present.

This is an operator-observed persistence result, not an independent application
database/content or credential audit. The operator explicitly declined a new
post-Stage-C raw backup.

## What was fixed to get here

- Physical p10 was repaired and passed a complete read-only fsck.
- A verified post-repair backup was acquired (`05f86fda…`).
- Stage B fixed-file two-boot persistence passed.
- Stage C first boot reached Android.
- The first reboot left the ext4 journal in needs_recovery state; the Stage C
  gate correctly refused to mount it.
- A journal-only replay (`e2fsck -p -E journal_only`) cleared recovery.
- Stage C then booted again and ran Android with repaired p10.

No format, cache-p9 mount, factory reset or partition change was used.

## Current limits

- `/cache` is still tmpfs. p9 was never mounted or verified for persistent use.
- No application database or content-integrity comparison was performed.
- The current p10 contains Stage C Android writes and the Stage B test directory.
  The operator declined a fresh post-Stage-C backup; this is accepted as an
  explicit scope decision.
- Abrupt power-off after Android can set needs_recovery again; clean shutdown is
  required before normal reboots.
- No sleep/LP2/storage power test was combined with Stage C.

## Next gate

Do not start Stage D or cache persistence. If further testing is needed, first
define a clean-shutdown procedure and acquire a fresh backup of the current
repaired/Android-written p10.

## Post-shutdown recovery state

A later Android shutdown attempt became stuck at “Shutting Down.” The tablet
was force-cycled, which set p10 `needs_recovery`; a journal-only replay returned
exit 0 and cleared it. The final read-only inspection now shows:

```text
PART_RO p10 1
EXT4_MAGIC data 53ef
EXT4_FEATURE_INCOMPAT data 42000000
RO_MOUNT_OK data
```

p10 is clean and read-only.

p9 cache was not mounted or modified. It currently shows:

```text
EXT4_MAGIC cache 53ef
EXT4_FEATURE_INCOMPAT cache 46000000
RO_MOUNT_OK cache
```

The cache remains unverified and has pending recovery; Stage C continues to use
fresh tmpfs cache, not p9. Do not treat cache as persistent.

## Final boundary

Persistent `/data` and Android boot are verified. Cache persistence, app/content
audit and clean shutdown automation are not. No further tablet writes should be
made without a new backup and a separate clean-shutdown plan.

## Repeated Stage C reboots — passes

Two additional full reboots using the corrected reboot-tolerant Stage C image
(`183597ba…`) were captured:

| Boot | pstore boot ID | data | cache | p10 | p9 | Android |
|---|---|---|---|---|---|---|
| 2a | `c22ec4ad-5e1a-4499-9e7d-1a9fa2634aec` | p10 ext4 rw | tmpfs | 0 | 1 | SurfaceFlinger/zygote running |
| 2b | `d11dadc3-2053-4f27-878c-7d511843fbcd` | p10 ext4 rw | tmpfs | 0 | 1 | SurfaceFlinger/zygote running |
| 2c | `368af1fb-f6a5-427b-961d-825200ffaab3` | p10 ext4 rw | tmpfs | 0 | 1 | SurfaceFlinger/zygote running |

Both reports validated in `android44-persistent` mode and reached
`exec_original_android_init`. The pstore boot IDs differ, confirming separate
kernel boots. The ext4 journal recovery gate accepted pending recovery after
forced power-offs and mounted p10 read-write normally.

No cache-p9 mount, Stage D, format or factory reset occurred. A third boot also passed, giving three distinct boot IDs and three successful
Stage C launches.
