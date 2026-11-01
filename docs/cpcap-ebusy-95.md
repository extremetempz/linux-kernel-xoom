# Repeated LP2 -EBUSY diagnostics — Image 95

Image 94 proved one complete LP2 cycle with the CPCAP IRQ-mask fix:

- physical wake passed;
- `LP2TEST_CPCAP_IRQ_ERRORS 0`;
- `WG_PM94_CPCAP_SUSPEND ... irq_masked=1`;
- `WG_PM94_CPCAP_RESUME ... irq_masked=0`.

The second cycle then failed before platform entry:

```text
sh: write error: Resource busy
LP2TEST_WRITE_RC 1
LP2TEST_AFTER completed=1 last_result=-16
```

Image 95 adds diagnostics only:

- `WG_LP2_STORE result=<ret>` in the LP2 sysfs store.
- `WG_PM95_CPCAP_SUSPEND_REJECT reason=owner|lock|owned` in the CPCAP
  suspend callback.
- The LP2 helper now always emits the filtered dmesg and CPCAP error count,
  even when the sysfs write fails.

Image:

`artifacts/lp2i-ready/wingray-android44-gpu.img`

- 4,218,880 bytes
- SHA-256 `9f60f2abf8c94e6997f6b329b486aa6b7bbe14d4fb96cbefeab57cf6f8871e8b`
- Not flashed.

Do not start the power campaign. First reproduce the `-16` once with Image 95
and read which reject path/marker appears. Repeated-cycle and power readiness
remain unproven.
