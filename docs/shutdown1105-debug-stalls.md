# Shutdown1105 hardware debug — blocked at p10 remount

These diagnostics are not a shutdown fix and were not merged into main.

## Confirmed sequence

The init class stops and clean-shutdown script start. Markers progress through:

```text
script_begin
initial_sync_ok
private_cache_ok
private_data_ok
before_cache_ro
after_cache_ro
before_data_ro
```

The p9 cache read-only transition succeeds. The p10 `/data` read-only transition
does not complete.

## Diagnostics added

- Persistent stage markers in the shutdown script.
- Init class-stop markers.
- A p10-first ordering debug build.
- A bounded worker supervisor.
- Attempts to write the blocked worker status/wchan/stack to p9 cache and p10.
- Cache is remounted writable at script entry only in the debug build.

## What failed

The p10 remount worker does not complete within 300 seconds. The stall report
cannot be reliably written:

- p9 may already be read-only;
- p10 is frozen in the remount;
- the process stack may be blocked in an uninterruptible kernel path.

No stall stack has been recovered. The exact kernel wait remains unidentified.

## Images

- `artifacts/shutdown1105-debug4-ready/wingray-android44-persistent.img`
  SHA256 `b31d645017b93b8b7a721548e9f8cb03cc6e5c487a753c6826956099d21e16d2`
- `artifacts/storage-inspect-debug4-ready/wingray-android44-persistent-inspect.img`
  SHA256 `cea6ebdab9cd96a1f669bc523f7123be28cb69b2d38df8d842bfef868ac8c5d5`

These are local diagnostic artifacts, not committed.

## Boundaries

- Main was fast-forwarded to `1652247`, but its RO-remount-first shutdown
  procedure does not complete on hardware.
- Do not use the main shutdown image as a verified fix.
- No format, repair or Stage E was performed.
- p9/p10 storage remains healthy; only shutdown is unresolved.
