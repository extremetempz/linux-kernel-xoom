# Candidate 16: remove a freed-init-code call from runtime tracing

Prepared 20 October 2026. The boot-only test, original restoration and bounded trace retrieval are
complete. Retain candidate 15's
USB/eMMC diagnostic and corrected lowmem sizing; change only the runtime
trace guard and the fresh cookie `0x584d0010`.

Candidate 15 reached basic driver setup, then recorded a die PC resolving to
`of_get_flat_dt_root()` in freed init text. The new `run_init_process()` trace
was using an early-only flat-DT guard after `free_initmem()`. A compiled
reproduction with the init section inaccessible fails at the same address.
See [candidate 15](trace-boot-attempt-15.md) for the evidence and limitations.

The corrected static helper checks the persistent mapping-readiness flag,
then retains the magic/version/cookie validation in the mapped write helper.
Only Wingray's `map_io` sets readiness after installing the one-page mapping.
There is no runtime flat-DT traversal or allocation. Donor correction
`6a0ba3a4` is patch 0023; the independent fresh-cookie change `f165d562` is
patch 0024.

The actual compiled init-exec wrapper passes eight controlled cases with all
init memory inaccessible: success, ENOENT, ENOEXEC, EACCES, mapping not ready,
wrong cookie, wrong version and wrong magic. Only filename lookup and exec
are stubbed; the actual wrapper/trace code executes. The fixture checks the
return status, argument handoff and exact phase stores. It reproduces the
old candidate 15 call into freed code as a control. This does not execute a
real ELF loader or establish userspace startup on hardware.

The diagnostic image build, boot-image audit, static-map guards, bounded
panic helper, fatal-entry guards, MMU snippets and converter/start-kernel
checks passed. Original images remain preserved. Hardware preflight and the
boot-only test/restoration/trace cycle subsequently completed as recorded
below. No Android boot, USB or eMMC success is claimed from offline checks.

Kernel-plus-DTB SHA-256:
`4f649b0795b66e8aead7c40649214caafef7b92973256ccf744345109050cc8d`.
Diagnostic-image SHA-256:
`3f4d454fb6707c5752ab4de15d4a24560040b24f8bb18d5bc42b34c786e6cdf4`.

## Physical result

A valid format-2 record with fresh cookie `0x584d0010` reports phase `0x421`,
`init_exec_succeeded`. The init-exec wrapper returned zero. The earlier fatal
PC in freed flat-DT code is absent. This confirms progress beyond the
candidate 15 diagnostic lifetime fault and acceptance of the RAM-disk init
executable; it does not establish a running Android framework or UI.

The first-fatal word is the panic sentinel and the retained 12-byte prefix is
`Attempted to`. This is consistent with the kernel's init-death panic path,
but this prefix alone does not distinguish it from the idle-task variant or
supply an exit status/signal. The next candidate must capture the PID 1 death
status explicitly. No USB serial reached this VM during the observation.

Full original boot/recovery readbacks match after restoration, and the working
Android ROM reached boot complete on Linux 2.6.39.4. The first verification
transfer was incomplete and stopped before any trace mapping. Smaller
read-only chunks subsequently verified both images; exactly one bounded
snapshot was taken. Android remained running with unchanged boot ID and no
new fault during retrieval; the temporary reader was removed.

A separate source/config audit explains a definite USB limitation: the donor
builds `phy-tegra-usb.o` only under `USB_EHCI_TEGRA`. The diagnostic requested
an undefined `USB_TEGRA_PHY` symbol, so the resolved config had `USB_PHY` off
and the PHY implementation absent. The compiled UDC probe's PHY lookup
therefore becomes the `-ENXIO` stub. Candidate 17 separates the actual PHY
option from EHCI and verifies both config and linked symbols. This is a
confirmed build/configuration defect; corrected hardware USB operation is
still untested.

Raw captures remain private in `artifacts/trace-boot-attempt-16-prepared/`.
Restoration hashes: boot
`64b45fa5b2127685310dcbd58acc5a154e5b7d54c7535354211eb87a5066e588`,
recovery
`5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606`.
