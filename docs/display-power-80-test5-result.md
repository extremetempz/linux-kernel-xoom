# Display 80 Test 5 — backlight-only hardware pass

27 October 2026. Image `display80fbtest5`, SHA-256
`02ab70c2595fff650b71eb00e920bb3a3a8c8afaeed69c4421398563aa155591`.

The physical Xoom was flashed and tested. Power off/on works, the backlight is
fully extinguished, and it restores without a scan line. The DC remains
enabled throughout.

Evidence from `artifacts/display80-fbtest5/fb-blank-test.txt`:

```text
[ 106.178352] Wingray backlight off: blank=4 dc=1
[ 106.949052] Wingray backlight on: dc=1
[ 108.461635] Wingray backlight off: blank=4 dc=1
[ 108.837804] Wingray backlight on: dc=1
[ 207.926751] Wingray backlight off: blank=4 dc=1
[ 208.173168] Wingray backlight on: dc=1
[ 210.718358] Wingray backlight off: blank=4 dc=1
[ 210.775912] Wingray backlight on: dc=1
[ 306.393462] Wingray backlight off: blank=4 dc=1   # fixed FBTEST
[ 307.440916] Wingray backlight on: dc=1
```

`fb0/state` stays 0 and is not authoritative. Every transition reports
`dc=1`; the controller was never disabled.

## Accepted scope

- LP8550 backlight off/on: **hardware pass**
- Android power-button blank/wake: **hardware pass**
- Display-controller power-down/resume: **not implemented**
  - The previous `dc=0`/`dc=1` experiment left the panel dark with a scan
    line after re-enable, even though the kernel reported `dc=1`.
- Suspend-to-RAM and deep sleep: **not implemented / gated**

The DC power-down must not be re-enabled until a proper panel reset/power
sequence is established. Backlight-only is the stable display power state.
