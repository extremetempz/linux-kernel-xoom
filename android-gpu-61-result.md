# Image 61 result: clock and P3 fixes verified; LCD still blank

25 October 2026. One boot-only test of
`artifacts/androidgpu61-ready/wingray-android44-gpu.img`
(SHA-256 `e9b626f22971aa4b2a7fdb0ea3dda377524b9d7f6ad7db2ff6823dd309c62949`)
was captured with a fresh nonce/integrity-verified USB report. The operator
reports a blank screen.

## Verified improvements

- The legacy DC no longer logs `can't divide 65000000 clock to 66400000`.
  The nvhost clock-default fix was effective: the DC completed probe and
  mode programming.
- The LP8550 readback now matches the production table:
  `a1=67`, `a2=bf`, `a3=3f`, `a4=08`, `a5=ea`, `a6=64`, `a7=2a`.
  No LP8550 probe failure is logged.
- DC IRQ 21 advanced from **0** in Image 60 to **18**. SurfaceFlinger reports
  `flips=17`, so the display path ran for an initial interval.
- Android still reaches `sys.boot_completed=1`; SurfaceFlinger still reports
  NVIDIA Tegra OpenGL ES 2.0 and the NVIDIA HWC; storage geometry still
  matches; both CPUs, PL310, touch and USB remain present.

## Not yet established

- Whether the backlight device is registered and enabled at report time.
- Whether the DC is enabled or was disabled after the initial frames.
- The live PLL_C/disp1 rates and pixel-clock divider.
- The exact panel mode (`h_ref_to_sync`/`v_ref_to_sync`) in use.
- Whether the framebuffer window was ever posted with valid pixels.

The existing `display-report.sh` rejected the `-gpu` release, so the report
contains only `XOOM_DISPLAY_DENIED_RELEASE`; no backlight, clock or DC debugfs
state was captured. The low IRQ count (18 over ~116 s) and the 17 flips show
the DC did not remain continuously active, but the reason is not yet known.

## Next step

Image 62 is a diagnostic-only rebuild of the same kernel with the `-gpu`
release permitted in `display-report.sh` and read-only backlight, DC debugfs,
`dumpsys display` and `dumpsys power` capture. It does not change the display
or backlight code.
