# Retained-console candidate 83 review

27 October 2026. Reviewed the merged ramoops/pstore PR on top of the accepted
IRQ/backlight baseline. No device operation or flash was performed.

## What is correct

- Patch 0154 supplies the `memory-region` phandle required by this donor's
  `ramoops_parse_dt()`. The reservation is split without changing the
  `[0x1fe00000, 0x20000000)` union:
  - legacy console `0x1fe00000..0x1fefffff`
  - ramoops `0x1ff00000..0x1fffffff`
- The new trace profile keeps IRQ-only CPCAP ON and backlight-only display;
  DC resume and suspend remain disabled.
- pstore mounting is guarded by the DT marker, read-only, and failure does
  not stop USB diagnostics.
- The PSTORE path has a separate 2 MiB payload / 3 MiB wire limit; normal
  REPORT remains 512 KiB.
- The report preserves the full configured console/record/pmsg set and
  reports truncation rather than silently dropping data.

## Offline verification

The trace donor was applied through patch 0154 and built:

`artifacts/trace83-review-ready/wingray-android44-gpu.img`
Size 4,149,248 bytes.
SHA-256 `9d7e357996403b6ad896d783f10487512e0853575dda73193f4d65ebc59fc329`.

Passed:

```text
retained-console reservation/phandle/no-overlap gates
2 MiB PSTORE framing and 1.5 MiB report budget
full-size fixture capture without writes/deletes
IRQ-only/backlight profile gates
actual CPCAP ON handler and existing display/battery/radio tests
```

Manifest: `retained_console_test=true`,
`retained_console_hardware_validated=false`,
`dc_resume_experimental=false`, `power_key_polling=false`,
`soc_suspend_enabled=false`.

## Findings

1. **The documented `6e8d2b08…` image hash was not reproducible.** The
   reviewed build produces `9d7e3579…` with the same size. The docs hash
   should be refreshed after applying the exported patch series and this
   repository's corrected 0151 config.
2. **Pstore retention is still unproven.** The binding and mount are now
   plausible, but no hardware warm-reset test has been run. `/sys/fs/pstore`
   being empty on first boot proves neither success nor failure.
3. The PSTORE host timeout was raised from 30 s to 90 s, maximum 300 s, so a
   full retained-console transfer is not cut short by the old 60 s ceiling.
   This is a host-tool change only; no image rebuild is needed.

No DC, suspend, regulator or charging change was made. Test 5 remains the
conservative rollback.
