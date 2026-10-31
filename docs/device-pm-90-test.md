# Image 90 review and hardware-test procedure

1 November 2026. Source review only; **Image 90 was not flashed or tested**
in this work. The prepared image and captures are not present in this
workspace, so earlier hardware claims cannot be independently reproduced.

## Source review

The selected CPCAP transaction is correctly bounded:

- It runs only inside the existing freezer preparation path and only on an
  exact root `1` request.
- It takes `pm_mutex`, its own test mutex and the CPCAP device mutex with
  trylock, so a frozen task cannot be required to release a lock.
- `pm_generic_suspend()` dispatches the actual `cpcap_wingray_pm_suspend`
  callback; `pm_generic_resume()` dispatches the matching resume callback.
- Suspend acquires one parent wake reference and refuses a pre-existing
  owner. Resume releases only `pm_cycle_owned`, never a manual owner.
- A failed arm that retains a reference is tracked as `pm_cycle_owned` and
  unwound by resume. A resume/cleanup failure remains recorded and blocks
  later cycles.
- Device references, device lock and `wake_arm_lock` are balanced on every
  tested path.
- The SPI controller remains active; no callback performs a CPCAP transfer
  after a parent suspend.
- FREEZERTEST is unchanged. Ordinary `pm_suspend()` remains blocked.

No functional defect was found in the selected-callback stage. It is not
full DPM ordering, late/noirq, SPI-parent suspend, LP2 or wake from sleep.

## Hardware test procedure (operator-controlled; do not auto-run)

Preconditions: Image 89 rollback and original boot/recovery backups verified;
battery sufficient; USB serial and physical recovery available.

1. Boot-only flash Image 90, allow Android to settle, reconnect serial.
2. Save a fresh normal REPORT and PSTORE.
3. Confirm status is exactly:

   ```text
   completed=0 last_result=0 selected=cpcap whole_tree=0 cpu_sleep=0 ordinary_sleep=blocked
   ```

4. Run once:

   ```sh
   python3 scripts/run-devicepm-test.py \
     --output-dir artifacts/devicepm90-cycle1
   ```

5. Expected:

   ```text
   DEVICEPMTEST_WRITE_RC 0
   DEVICEPMTEST_AFTER completed=1 last_result=0 selected=cpcap whole_tree=0 cpu_sleep=0 ordinary_sleep=blocked
   DEVICEPMTEST_COUNTER_ADVANCED_1
   DEVICEPMTEST_PROCESS_RC 0
   ```

   Kernel log should show `WG_PM90_CPCAP_SUSPEND result=0`,
   `WG_PM90_CPCAP_RESUME result=0`, `WG_PM90_CPCAP_COMPLETE suspend=0
   resume=0` and `WG_PM90_TASKS_THAWED result=0`.
6. Immediately save REPORT/PSTORE/pm-snapshot. Verify CPCAP `owned=0`,
   `parent_wake=0`, errors unchanged, CPUs0–1 online, same Android session,
   power-button backlight off/on, touch, display and USB diagnostics.
7. On any failure, preserve logs and stop. Do not retry automatically, do not
   proceed to DPM, and do not enable LP2.

No SPI-parent sleep, display/GPU system PM or hardware sleep is part of this
test.
