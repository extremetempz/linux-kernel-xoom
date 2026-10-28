# Candidate 84 — two corrected-console warm-reset comparisons pass

28 October 2026. Tested the exact ECC candidate documented in
[the build and procedure](suspend-retention-84.md):

- Image SHA-256: `eaa6486d9bf887e3b2bdb49215c3d58b289417bdecdc90254138150fa9104e7e`
- Image size: 4,151,296 bytes; kernel patch 0156 / source `b3393c36`.
- `wakeirqecc`: CPCAP ON IRQ-only and backlight-only display; DC shutdown,
  PM/SUSPEND and DVFS disabled.

The operator explicitly authorised the boot-only flash. Fastboot identified
`xoom-wifi`, confirmed transfer and write, and accepted the subsequent boot
command. The original boot/recovery **backup files** passed their recorded
SHA-256 checks. Recovery and partition layout were not written. The original
boot image has **not** been restored after this test; candidate 84 remains
installed and running. No live partition readback is claimed here.

## First ECC boot / baseline

The operator observed the Android Welcome screen. A verified normal report
confirmed `sys.boot_completed=1`, SurfaceFlinger/zygote operation and matching
full eMMC/ten-partition geometry under the read-only-system/RAM-data policy.

The fixed PSTORE snapshot confirmed the intended bound backend, read-only
mount, DT ECC size 16 and memory layout:

```text
RAMOOPS_DT_ECC_HEX 00000010
PSTORE_MOUNTED_yes
PSTORE_MOUNT_RC 0
RAMOOPS_BOUND /sys/bus/platform/drivers/ramoops/1ff00000.ramoops
RAMOOPS_PARAM mem_address 535822336
RAMOOPS_PARAM mem_size 1048576
RAMOOPS_PARAM record_size 131072
RAMOOPS_PARAM console_size 524288
RAMOOPS_PARAM pmsg_size 131072
```

The full kernel log records `ramoops: attached ... ecc: 16/0`. The second
number is the context's unspecified block-size field; the existing donor
sets the zone's default block size to 128 internally. The independent probe
was 379 bytes, including its UUID, fixed pattern and SHA-256. Its content/hash
matched the expected value.

Five old-format header errors appeared during this **first** ECC boot and
there were no recovered old files. These old no-ECC headers are incompatible
with the new layout. They were not counted as fresh retention failures or
silently cleared through pstore. This transition sample is not a reset pass.

## Two operator-controlled resets into the same image

The operator used Power + Volume Up, released the buttons and allowed the
same installed image to boot, then reconnected USB serial to VMware. No
intervening original-ROM restoration or other image flash occurred. Each
PSTORE response was saved privately and independently revalidated against
its original serial frame, nonce, size, saved payload and SHA-256.

| Comparison | Boot transition | Old console bytes | Known probe | ECC corrected bytes | Unrecoverable blocks | Verdict |
|---|---|---:|---|---:|---:|---|
| Baseline → reset 1 | `a75da3b2…` → `824832a5…` | 117,090 | Exact previous marker and 379-byte probe | 19 | 0 | Pass |
| Reset 1 → reset 2 | `824832a5…` → `dbc8fc35…` | 125,340 | Exact previous marker and 379-byte probe | 25 | 0 | Pass |

Both comparisons used `scripts/check-pstore-retention.py`. The checker
searched **old `console-ramoops-0`**, not current dmesg or a pmsg substitute.
Both returned `gate_passed=true`. Each serial payload matches its own saved
checksum; the recovered known probe matches the previous capture exactly.
Current boot IDs differ, and no console truncation occurred.

Normal reports after each reset passed framing and storage-policy checks.
The first snapshot after reset 2 was taken while Android was still starting:
SurfaceFlinger and zygote were running but `sys.boot_completed` was absent.
One later settled report confirmed `sys.boot_completed=1`. It was the same
boot, not an additional reset sample. The post-reset IRQ status reports
`polling=0`, LIC parent, domain index 23, zero errors and
`soc_suspend=disabled`. No new key-event exercise or radio reconnect test was
performed during these captures.

## Accepted result and limits

**The planned two-cycle, known-console-probe warm-reset retention gate
passes with ECC correction.** This is a corrected-retention result: it is
not error-free raw RAM retention. The 19/25 counts cover corrected symbols
in the console zone, not a count of damaged probe characters. The underlying
source of corruption remains unknown and must not be described as fixed.

The exact known probe and its digest survived each comparison. ECC reported
zero unrecoverable console blocks. That does not establish every byte of the
whole retained log, behaviour beyond ECC's correction capacity, deliberate
panic-record recovery, retention after a DC hard hang, power loss, cold boot,
another bootloader path, or long-term reliability. No suspend, hardware sleep
wake, DC power-down/resume or power-consumption measurement occurred.

Raw reports and wire captures remain under ignored private `artifacts/`:
`retention84-before`, `retention84-after1`, `retention84-after2`, their normal
reports and `retention84-after2-settled`. Comparison summaries are in
`artifacts/retention84-deployment/comparison1.json` and `comparison2.json`.
No private raw logs or original ROM files are published with this result.

## Next development gate

Keep this ECC-enabled image and the known-good IRQ/backlight rollback image.
The next **separate** candidate can instrument the combined IRQ/DC path to
locate the existing hang, retaining the same reserved-memory/ECC layout for
matched log recovery. Add checkpoints before/after DC blank/disable, locking,
clock transitions and enable/first-frame completion; avoid using printk inside
spinlocked or clock-disabled register paths. Review the actual locks/callers
before choosing checkpoint locations.

Hard-hang recovery remains a distinct validation step. Do not substitute the
original ROM as a pstore recovery reader, and do not enable system suspend or
LP0/LP1/LP2 merely because these normal warm-reset comparisons passed.
