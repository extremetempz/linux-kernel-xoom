# Retained-console candidate 83 review and size-binding fix

27 October 2026. Reviewed the merged ramoops/pstore PR after a hardware run.

## Root cause found in the hardware report

The trace image mounted pstore read-only but the backend was unbound:

```text
PSTORE_MOUNTED_yes
RAMOOPS_BACKEND_UNBOUND
RAMOOPS_PARAM mem_size 0
RAMOOPS_PARAM record_size 4096
RAMOOPS_PARAM console_size 4096
RAMOOPS_PARAM pmsg_size 4096
```

Full dmesg showed:

```text
ramoops 1ff00000.ramoops: failed to parse property record-size: -75
ramoops: probe of 1ff00000.ramoops failed with error -75
```

`-75` is `-EOVERFLOW`. This donor's `ramoops_parse_dt_size()` uses
`of_property_read_u64()`, but patch 0154 left the inherited one-cell (u32)
`record-size`, `console-size` and `pmsg-size` properties. The `memory-region`
phandle was correct, but the size parsing failed first.

## Fix

Patch 0155 changes the trace consumer's three sizes to `/bits/ 64`:

```text
record-size  = /bits/ 64 <0x20000>
console-size = /bits/ 64 <0x80000>
pmsg-size    = /bits/ 64 <0x20000>
```

The reservation partition and values are unchanged. The validator now expects
u32 in the baseline DT and u64 in the trace DT for these three inherited
properties. No driver or generic DT behavior was changed.

## Offline verification

Built image:

`artifacts/trace83fix2-review-ready/wingray-android44-gpu.img`
Size 4,149,248 bytes.
SHA-256 `42a2699c9f380a7fce50d2b3348780a9a588a9b3e28a23025168350c4186edfd`.

Compiled DT now contains:

```text
record-size = <0x0 0x20000>
console-size = <0x0 0x80000>
pmsg-size = <0x0 0x20000>
```

Passed: retained reservation/phandle/no-overlap checks, full-size pstore
fixture capture, 2 MiB PSTORE framing, IRQ-only profile, CPCAP ON handler,
display/backlight and existing radio/battery regressions.

## Still required

This should make `ramoops` probe, but retention across a warm reset is still
**hardware-unverified**. Flash this image, capture PSTORE, warm-reset into the
same image, and verify the previous boot marker in an old console record.

The PR's documented `6e8d2b08…` and the earlier `9d7e3579…` hash are both
superseded by this fixed build. Test 5 remains the rollback. Do not enable
DC or suspend before the retention gate passes.

## Hardware binding result (pre-reset)

The fixed image was booted. The first PSTORE snapshot reports:

```text
CURRENT_BOOT_ID 5a938e4d-83e4-4bdb-a8c5-1370ef46fa72
PSTORE_MOUNTED_yes
PSTORE_MOUNT_RC 0
RAMOOPS_BOUND /sys/bus/platform/drivers/ramoops/1ff00000.ramoops
RAMOOPS_PARAM mem_address 535822336   (0x1ff00000)
RAMOOPS_PARAM mem_size 1048576
RAMOOPS_PARAM record_size 131072
RAMOOPS_PARAM console_size 524288
RAMOOPS_PARAM pmsg_size 131072
```

`ramoops` now binds and the parameters match the intended layout. The pstore
directory is empty on this first valid boot, which is expected. Retention
across a warm reset is the remaining gate.

## Warm-reset retention result (partial)

The first warm reset preserved the previous console:

```text
CURRENT_BOOT_ID 64f4ed82-2568-4b16-8f43-c484eefb94bd
PSTORE_FILE /sys/fs/pstore/console-ramoops-0
PSTORE_BYTES original=78329 captured=78329
```

The old record contains the previous boot marker, but with one corrupted
character:

```text
5a9s8e4d-83e4-4bdb-a8c5-1370ef46fa72
```

The first boot reported:

```text
5a938e4d-83e4-4bdb-a8c5-1370ef46fa72
```

`s` is not a valid UUID hex digit, so this is not a reporting typo. The
ramoops backend and mount are correct, boot IDs differ, and the previous
console survived, but the retained record is **not bit-identical**. Strict
retention validation therefore fails for now; determine whether the byte
corruption is reproducible with another warm reset before trusting pstore as
the sole failure log.

No DC or suspend enablement follows from this result.
