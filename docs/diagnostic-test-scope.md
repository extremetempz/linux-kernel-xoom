> **Images 28/29, 22 October 2026:** The user made the real Android lockscreen the objective. Standing boot-only/restoration cycles cover minimal display/backlight testing toward that objective. Image28 captured explicit LCD pull-capability and guarded backlight-probe failures; full original boot/recovery verification and original Android completed afterward. Image29 separately corrects shared pull mapping and improves rejection evidence. Diagnostic framebuffer writes and bounded backlight current control are volatile; no Android mount/write, recovery write, repartition, arbitrary MMIO, EEPROM programming or reserved-RAM retrieval.

> **Image 27 cycle complete, 22 October 2026:** Two fresh checksum-verified reports retained full capacity/all ten BigPart extents and completed all twelve fixed LP8550 reads (identity FC). PB2 is claimed output-high by the shared panel regulator. Original boot restored; both full original readbacks verified; original Android running. No background test or reserved-RAM retrieval remains active.

> **Image 27 authorized, 21 October 2026:** The user asked to continue porting and then explicitly requested flashing. Test the isolated shared-panel-supply/I2C readiness profile under the existing boot-only/restoration scope. Fixed known-address register reads only; no display-clock/backlight programming, touch/PMIC/CPU-rail driver, Android mount/write, recovery write, repartition or reserved-RAM retrieval.

> **Image 26 cycle complete, 21 October 2026:** Two independent fresh checksum-verified USB reports match full disk capacity and all ten BigPart extents. Original boot restored; full boot/recovery readbacks verified and original Android running. No Android mounts or reserved-RAM reads. No device test or background watcher remains active.

> **Latest work, 21 October 2026:** Image 24 passed fresh USB integrity and all ten partition extents but exposed a capacity discrepancy. Image 25 confirmed the scoped capacity fix and exposed a masked GPT-option prefix bug; originals are fully verified after restoration. Image 26 tests the separately committed parser correction under the same boot-only authorization. No Android mounts, recovery write, repartition or reserved-RAM read.

> **Latest work, 21 October 2026:** The user requested the next porting step. Image 24 retains the tested candidate-23 kernel and changes only RAM diagnostic transport for fresh, checksummed, read-only eMMC/BigPart reports. Standing boot-only test/restoration authorization applies. No Android mounts, repartitioning, recovery write or reserved-RAM read is planned.

> **Build 23 cycle complete, 21 October 2026:** USB enumeration and a framed diagnostic boot report were captured. Both original images are fully verified after restoration, Android is running, and the single bounded GPIO/USB trace was retrieved. No further test or background watcher is running.

> **Latest work, 21 October 2026:** The user requested “look at the logs, find out why it failed and fix it”, including the bigger picture. Candidate 23 corrects the GPIO/pinctrl dependency and adds a bounded read-only USB-switch state snapshot. Standing boot-only test/restoration authorization remains applicable; recovery, repartitioning and Android filesystem changes remain excluded.

> **Build 22 cycle completed, 21 October 2026:** The boot-only test, original restoration, full boot/recovery verification and one bounded trace retrieval are complete. Android is running. USB remains unobserved, with successful PHY/core/bind statuses and device/run state. No further test or background watcher is running.

> **Latest authorization, 21 October 2026:** The user returned and requested “okay i am back, please flash”. This resumes the paused work and authorizes building candidate 22 from the saved PHY timeout correction, boot-only testing, original restoration and verification, and bounded trace retrieval. Recovery, partition layout and Android filesystem changes remain excluded.

> **Latest instruction, 20 October 2026:** After build 21 restoration, the user requested “look at the error do a fix but don't do anything else as i am going to log ooff”. Finish the single trace retrieval already in progress, make the local source correction and bounded checks, then stop. Do not build another boot image, flash, start another hardware cycle, upload or monitor in the background until the user resumes.

> **Earlier authorization, 20 October 2026:** The user requested “look at the logs work out why usb wasn’t detected and redeploy”, authorizing the revised USB diagnostic boot-only test and original restoration/verification. Recovery, partition layout and Android filesystem changes remain excluded.

> **Build 20 cycle completed:** The authorized test is finished, original boot and recovery are verified, and the working Android ROM is running. No additional build, device test or background monitor was started.

> **Later on 20 October 2026:** The user resumed with “alright deploy pls”, authorizing the prepared build 20 boot-only test, original restoration and bounded trace retrieval. The earlier build-only hold is superseded for this test cycle. Recovery, partition layout and Android filesystem changes remain outside scope.

> **20 October 2026 — current user instruction:** Build the next patch/image locally, do not flash, and stop after the build. Earlier standing permission for repeated flash cycles is superseded. No further device tests or background monitoring until the user resumes and authorizes them.

# Diagnostic test authorization

On 19 October 2026 the user approved candidate 4 and stated:

> yea please do, you can just flash in future dont check with me

This provides standing authorization for subsequent diagnostic-kernel
**boot-partition** test cycles in this ongoing Wingray bring-up. Continue to
verify the candidate and target device, preserve every original and prior
candidate, restore the original boot image after each test, verify device
readbacks, and keep raw captures private. There is no need to ask for another
flash approval for each such candidate.

This scope does not expand to recovery flashes, repartitioning, unlocking,
erasing data, installing a ROM, or modifying an unrelated device. Requests for
power/volume button operation or VMware USB reconnection remain necessary
operator handoffs, not repeated approval requests.
