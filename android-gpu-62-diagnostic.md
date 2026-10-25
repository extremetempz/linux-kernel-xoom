# Image 62 diagnostic: capture backlight, DC and display-power state

25 October 2026. Diagnostic-only rebuild of the Image 61 kernel. No kernel or
display code changed; the built-in display report now accepts the `-gpu`
release and collects:

- backlight class, brightness, actual brightness, power and bl_power;
- LP8550 driver binding and `wingray_registers`;
- panel regulator state;
- `clk_summary`;
- `tegradc.0/mode` and `tegradc.0/stats`, plus a bounded register dump;
- `dumpsys display` and `dumpsys power`.

Image 62 is not a fix and is not expected to make the LCD visible. Its purpose
is to distinguish backlight-off from DC-disabled and to identify what disabled
the display after the initial 17–18 frames.

- Path: `artifacts/androidgpu62-ready/wingray-android44-gpu.img`
- Size: 3,637,248 bytes
- SHA-256: `0534a5a2b73194e8943919c21d081cf49ef2af547073f6e25a5ecee6e0710934`
- Kernel/DTB/config are the same as Image 61; only the built-in diagnostic
  report changed.

After boot, capture a fresh report into a new directory:

```sh
python3 scripts/capture-framed-diagnostic.py \
  --output-dir artifacts/androidgpu62-report1 \
  --storage-mode android44-readonly
```

Operator observation requested: whether any backlight glow or Motorola logo
appears during boot, and whether the panel is completely dark in a dark room.
