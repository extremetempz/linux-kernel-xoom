# Candidate 81 — hardware result

27 October 2026. The reviewed candidate was flashed and the operator reports
that display power off/on, DC resume and normal Android operation are all
working, with no scan line.

- Image: `artifacts/dc81-review-ready/wingray-android44-gpu.img`
- Size: 4,147,200 bytes
- SHA-256: `e02c7c41f5e95ed3f8155ce7d1761e355b98b0df4931fec7cedf08f2c71dc1ea`

This confirms the three software corrections are effective on this unit:

- native `href=11` / `vref=1` mode retained across the transition
- all scanout windows restored, not only the fbdev window
- DC blank/unblank serialized against legacy flips

The previous Test 5 image remains the known-good backlight-only rollback:

`artifacts/display80fbtest5-ready/wingray-android44-gpu.img`
SHA-256 `02ab70c2595fff650b71eb00e920bb3a3a8c8afaeed69c4421398563aa155591`.

## Still out of scope

- No suspend-to-RAM, automatic suspend, LP1 or LP0 was enabled or tested.
- No repeated-cycle count, overnight sleep or power-consumption measurement
  was supplied with this observation.
- The DC transition now works on this unit, but further long-duration and
  rapid-cycle testing is still advisable before treating it as permanent.
