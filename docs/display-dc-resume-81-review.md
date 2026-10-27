# Candidate 81 review — software verification

Reviewed merged main `e7dc91c` against Test 5 `e257af5`. No device operation
or flash was performed.

## The three claimed mismatches are real

1. **Native mode drift.** `tegra_dc_set_fb_mode()` round-trips through
   `fb_videomode`, which cannot carry Tegra `href`/`vref`; it caches
   `href=0` without programming the active DC. Patch 0151 retains the single
   native RGB mode (`href=11`, `vref=1`, pclk 66400000) and rejects mismatched
   fb modes.
2. **Window loss.** `_tegra_dc_controller_disable()` clears every window's
   ENABLED flag. The old resume restored only `fb->win`. Patch 0151 saves and
   restores all `DC_N_WINDOWS` flags while preserving addresses, strides,
   formats, geometry and pinned ownership.
3. **Flip serialization.** The old path did not exclude legacy Android flips.
   Patch 0151 holds `legacy_lock` across the DC transition and returns
   `-EBUSY` for a flip while `dc_blanked` is true, before pinning or
   fabricating a completion syncpoint.

The new `tests/test-wingray-dc-resume.py` passes against the patched donor:
native mode round trip, all-window restore with window 0 inactive, twenty
software cycles, timeout/IO/enable/readback failures and safe retry.

## Two defects found in the merged PR

1. **The new test failed as merged.** The `displaydc` defconfig repeated
   `# CONFIG_SUSPEND is not set`; the baseline-isolation assertion failed.
   Removing the duplicate makes the test pass. It is a config-only defect,
   but it means the PR was not green as merged.
2. **Patch 0151 is not applied to the tracked donor.** The donor is an ignored
   local tree. On a clean checkout the `displaydc` defconfig symbol has no
   backing Kconfig/code, `olddefconfig` drops it, and the profile silently
   builds the Test 5 backlight-only kernel. The build documentation must say
   to apply `kernel/patches/0151-...` to `sources/kernel-donor` first.

The documented image hash `70bb707d…` was not reproducible from the reviewed
tree. After applying 0151 and removing the duplicate config line, the local
build produced:

- `artifacts/dc81-review-ready/wingray-android44-gpu.img`
- 4,147,200 bytes
- SHA-256 `e02c7c41f5e95ed3f8155ce7d1761e355b98b0df4931fec7cedf08f2c71dc1ea`
- manifest `dc_resume_experimental=true`, `dc_resume_hardware_validated=false`

## What remains unverified

These are software fixes for real mismatches, not proof that the panel scan
line is gone. The previous failure was physical and could also involve panel
power/reset sequencing. Candidate 81 remains experimental; Test 5
backlight-only (`02ab70c2…`) remains the stable baseline.

Hardware acceptance, if authorized later: fresh baseline, one FBTEST in a
quiet session, then one Android power cycle, then repeated cycles; retain
Test 5 for rollback. Do not enable suspend.
