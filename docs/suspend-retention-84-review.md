# ECC retained-console candidate 84 review

28 October 2026. Reviewed the merged ECC/RS retention PR. No device operation
or flash was performed during this review.

## Code and offline validation

The ECC approach is coherent with this donor:

- `ramoops` already implements RS(8) in `ram_core.c`; the profile only adds
  the opt-in `ecc-size = <16>` consumer property.
- `ecc-size` is correctly read as u32 by `ramoops_parse_dt()`.
- The parser defaults `block_size` to 128 inside
  `persistent_ram_init_ecc()`; no extra DT block-size is required.
- The ECC profile keeps the already-fixed 64-bit log sizes, reserved-memory
  split, IRQ-only CPCAP path and backlight-only display; DC/PM/SUSPEND remain
  off.
- The boot probe is a multiblock console payload with an exact SHA-256 and
  is emitted only for the ECC DT marker.
- The retention checker validates the saved wire frame/hash, searches only
  `console-ramoops-0`, requires different boot IDs, requires the exact old
  probe, and rejects unrecoverable ECC blocks.

The fixed donor built and the relevant tests passed:

```text
pstore ECC RS recovery and uncorrectable-block reporting
boot probe content/hash/ECC-block coverage
retention checker accept/reject cases
2 MiB PSTORE framing and report bounds
retained-console reservation/phandle gates
IRQ/backlight and existing display/battery/radio regressions
```

One environment-only test (`test_server_pty`) failed because this host has no
available pty devices; it is unrelated to the kernel or pstore change.

## Build identity discrepancy

The PR documents:

- image `eaa6486d9bf887e3b2bdb49215c3d58b289417bdecdc90254138150fa9104e7e`
- size 4,151,296 bytes

The reviewed build produced:

- `artifacts/ecc84-review-ready/wingray-android44-gpu.img`
- size 4,147,200 bytes
- SHA-256 `d3c676368a579664de4f2852e47140ea569d82c52cc8682f3df4ce8ba752f2e0`

The discrepancy is likely from this checkout's corrected trace-83/0155
sources and host-script fixes, but it means the claimed image is not directly
reproducible from the merged tree.

## Hardware result cannot be independently verified

The result document names private artifacts:

```text
artifacts/retention84-before
artifacts/retention84-after1
artifacts/retention84-after2
artifacts/retention84-after2-settled
artifacts/retention84-deployment/comparison1.json
artifacts/retention84-deployment/comparison2.json
```

**None of these exist in this workspace.** The documented two-pass result is
therefore not independently checkable here. The correct next step is to copy
those private capture directories and run:

```sh
python3 scripts/check-pstore-retention.py \
  --before artifacts/retention84-before \
  --after  artifacts/retention84-after1

python3 scripts/check-pstore-retention.py \
  --before artifacts/retention84-after1 \
  --after  artifacts/retention84-after2
```

Until those checker runs reproduce `gate_passed=true`, the hardware retention
claim should remain documented-but-unverified in this checkout.

## Limits

ECC correction is not error-free raw retention; the observed 19/25 corrected
bytes still indicate an unexplained corruption source. The result does not
validate DC hard-hang recovery, panic recovery, cold boot, long-term retention
or suspend. Do not enable DC/suspend from this review.
