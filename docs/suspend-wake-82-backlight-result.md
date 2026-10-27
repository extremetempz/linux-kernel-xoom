# IRQ-only + backlight-only — hardware pass

27 October 2026. Image `wakeirqbl`, SHA-256
`7219443f7bfa2caf6be935ecb08162e7c05ef7e3988e5bf385890ecb07317f09`.

## IRQ path

```text
mode=irq-only polling=0 parent=59 chip=LIC hwirq=86
on_virq=115 on_domain_index=23 events=26 errors=0 state=0
soc_suspend=disabled
bank=1 status=c201 mask=fffb sense=6200 unmasked_pending=0000
bank=2 status=040c mask=ff7f sense=023c unmasked_pending=0000
bank=3 status=4000 mask=ffff sense=4000 unmasked_pending=0000
bank=4 status=0001 mask=3fff sense=0001 unmasked_pending=0000
```

The log shows real nested ON events, for example:

```text
Wingray ON IRQ-only registered: parent=59 virq=115 index=23; no polling
...
Wingray ON IRQ: count=9 sense=02bc pressed=1
Wingray ON IRQ: count=10 sense=023c pressed=0
...
Wingray ON IRQ: count=22 sense=023c pressed=0
```

There is **no** `CPCAP power key polling registered`, no `nobody cared`, no
disabled parent, no sense error, and no unmasked-pending bit.

## Display path

The same report contains repeated transitions:

```text
Wingray backlight off: blank=4 dc=1
Wingray backlight on: dc=1
```

Power button screen off/on succeeds repeatedly. The DC is never disabled and
there is no scan line. This isolates the earlier full-wakeirq failure to the
DC/candidate-81 path rather than the CPCAP ON IRQ path.

## Pstore limitation

The fixed PSTORE request works, but `/sys/fs/pstore` is empty:

```text
ramoops 1ff00000.ramoops: no memory-region phandle
```

The current 4.4 ramoops binding is not establishing a pstore region, so the
previous full-wakeirq failure could not be recovered. That needs a separate
reserved-memory/memory-region fix before relying on pstore for a suspend
failure.

## Status

- CPCAP ON IRQ-only path: **hardware-validated**
- LIC parent and dynamic virq: **hardware-validated**
- Polling absence: **hardware-validated**
- IRQ + backlight display cycles: **hardware-validated**
- Candidate 81 DC path: **not enabled here**; the earlier full-wakeirq failure
  remains consistent with that path
- Suspend-to-RAM/deep sleep: **not implemented or tested**

Test 5 remains the conservative rollback. Do not enable suspend yet.
