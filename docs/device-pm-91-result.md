# Image 91 hardware result — devices-only DPM and DC first-frame restore

1 November 2026. Hardware test of the `07544142…` image. This is a
**devices-only DPM** milestone, not CPU sleep, LP2 or deep sleep.

## Image

`artifacts/dpm91-dcfix-ready/wingray-android44-gpu.img`

- Size: 4,216,832 bytes
- SHA-256: `075441429bad1cf5c3d844dfef4d3d4cf6898e1b0865f2cde0cca28e88c2f565`
- Profile: `android44-devicepm91`
- Platform/CPU/syscore entry: blocked
- ECC16/pstore retained

## Same-boot evidence

The host lost USB while devices were suspended. The DPM result was recovered
from the same boot's normal report:

```text
[   85.170616] WG_PM91_FREEZER_COMPLETE selected=dpm platform_entry=0 cpu_sleep=0
[   85.173601] lp855x 0-002c: P3 backlight requested=102 effective=0
[   85.176819] tegradc tegradc.0: suspend
[   85.177944] PM: suspend of devices complete after 4.971 msecs
[   85.177958] suspend debug: Waiting for 5 second(s).
[   90.173055] tegradc tegradc.0: resume
[   90.406836] call tegradc.0+ returned 0 after 228300 usecs
[   90.583040] lp855x 0-002c: P3 backlight requested=102 effective=102
[   90.583578] PM: resume of devices complete after 410.623 msecs
[   90.791106] WG_PM91_DPM_COMPLETE result=0 platform_entry=0 cpu_sleep=0
[   90.794706] WG_PM91_TASKS_THAWED result=0 cpu_sleep=0
```

- Boot ID: `47bd83d8-3fdc-410d-acaa-59bbbbae6e32`
- `sys.boot_completed=1`
- Display: `mDisplayReady=true`, `Display Blanker: blanked=false`
- No `system resume scanout restore failed` message.
- The operator observed roughly five seconds of blanking, matching the
  `pm_test` hold, rather than the earlier ~30-second blank interval.

The preceding keep-power image also completed DPM with `result=0`; its display
was not restored for ~30 seconds. The `07544142…` image adds the DC window
flag/first-frame restore and is the image tested here.

## Accepted scope

Hardware-passed at this stage:

- task freeze/thaw;
- BCM4329 SDIO keep-power suspend;
- full-tree normal-phase `dpm_suspend`/`dpm_resume`;
- DC/backlight suspend/resume with first-frame restore;
- same Android session after thaw.

Not tested or still blocked:

- `dpm_suspend_late/noirq` and syscore;
- CPU1 offline/restart;
- platform LP2/LP1/LP0 entry;
- physical power-button wake from sleep;
- DRAM self-refresh, L2 disable across CPU power loss, timer continuity;
- automatic Android suspend, power measurement;
- final visual/touch/radio certification beyond the observed screen return.

## Transport caveat

`run-dpm-test.py` raises `Serial device disconnected` because the USB CDC ACM
gadget is one of the suspended devices. That traceback is not a DPM failure.
The fixed result remains readable from the same-boot normal report and the
on-device `/run/dpm-test.txt`; the host helper still needs a reconnect/status
path for a clean framed pass.

## Next gate

Do not enable LP2 from this result alone. Next:

1. confirm visible content, touch, power button, Wi-Fi/BT and battery;
2. add the separate CPU1 offline/online test;
3. review late/noirq and timer/L2/wake ordering;
4. only then prepare an entry-capable LP2 profile.

Keep the original boot/recovery backups and Test 5 rollback.
