# Stage D clean shutdown — blocked on p9 cache unmount

The persistent p9/p10 Android configuration still works, but clean Android
shutdown is not fixed.

## What passed

- All `class_stop` phases completed: late_start, main, core.
- The clean-shutdown script started.
- `sync` completed.
- No open `/cache` file descriptors and no `fuser` holders were found.
- `mount --make-private /cache` and `/data` completed without the script
  stopping at make-private.
- A host copy of current p9 replayed its journal and passed a full read-only
  fsck (exit 0).
- The earlier p9 cache write/reboot test passed.
- Forced shutdowns always recovered p9 and p10 through journal replay.

## What failed

The script reaches:

```text
before_cache_umount
```

and then blocks in cache unmount/remount. The data marker indicates
`after_make_private`, so peer-mount propagation was not the whole cause.

No open holders were present. This points to p9 cache writeback/journal teardown
in the kernel rather than an Android process holding files.

## Boundaries

- Stage D is **not complete**.
- No format, cache repair or Stage E occurred.
- No p9/p10 data loss was observed.
- Do not retry normal power-off with the current images.
- Normal Android use with p9/p10 persistent storage remains available.
