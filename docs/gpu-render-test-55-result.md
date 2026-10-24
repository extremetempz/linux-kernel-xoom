# Offscreen rendering attempt 55: no rendered result recovered

Hardware test/readback recorded 25 October 2026 (client timezone). **No live USB
report or rendered-pixel result was recovered. Acceleration remains unproven.**

The matched retained record has cookie `0x584d0055`, trace SHA256
`616c7ff88b9a7aac643efe2009a696c914675954aa97c67a307cbac7b240aaa9`. CPU1 is online; host, GR2D and GR3D stage 61/result 0;
kernel stage 7/exec result 0; USB registration result 0; no retained panic.
Last initcall `clk_disable_unused` returned 0. These establish startup progress,
not GPU job execution, probe entry or a running reporter. Motorola logo and no
guest USB do not locate the stop or prove a kernel hang.

Userspace/reporter markers are zero, as in independently successful build 54.
Their transport was therefore investigated before another rendering attempt.

## Reproduced diagnostic defect

The exact SHA-pinned static BusyBox was temporarily placed in a unique `/dev`
RAM directory on the restored original ROM. Its existing strace observed
`printf '1\n'` directed only to `/dev/null`:

```
writev(1, [{"1", 1}, {"\n", 1}], 2) = 2
```

Linux 4.4 falls back to separate scalar writes for each iovec when a character
device lacks `write_iter`. The diagnostic device accepted only count 2, so it
rejected these count-1 fragments. Patch 0106 adds a proper bounded `write_iter`
that gathers exactly two bytes and uses the same fixed-command validation.
Privilege, length, stale-header and command restrictions remain. Actual compiled
fixtures cover split buffers, partial copies, invalid lengths/commands and
permission rejection. This fixes missing diagnostic evidence, not an identified
GPU execution defect. Temporary tracing files and the BusyBox copy were removed.

## Device preservation and next test

The original boot image was restored. Android returned over ADB after the
requested minute; both complete original partition hashes match. The guarded
reserved-page read completed without a newly detected original-kernel fault,
and its temporary RAM reader was removed. No restoration remains pending.
Private evidence: `artifacts/gpu-render55-attempt1/`.

Next separate USB baseline capture from an explicit, once-only release of the
same bounded probe. Add diagnostic channel open/write/pin/submit/ioctl progress
without changing driver return values or hardware programming. Do not claim a
GPU fix, successful render or cause of USB absence from this record.
