# Offline98 p10-only repair environment — built, not flashed

This is a **dangerous writable repair gate**, not an automatic repair. It was
built and offline-checked only. No tablet access, flash, mount, fsck, repair or
userdata write has occurred.

## Image

`artifacts/offline98-repair-ready/wingray-offline98-repair.img`

- 3,956,736 bytes
- SHA256 `efd7163e4452ab32477e13775ff2af4aa04769f59de10164a64b2a92c28d0874`
- Internal kernel initramfs; external ramdisk empty.
- Serial gadget only; no Android, TWRP, mass storage or cache mount.
- Whole disk, p8 and p9 remain read-only.
- p10 is released only by the fixed `storage-policy` helper after the operator
  sends `REPAIR_P10` followed by the exact `REPAIR_P10_CONFIRM` nonce.
- The helper requires the repair DT marker and
  `/bin/storage-data-approved`; there is no cache approval.
- No automatic mount, fsck, repair, reboot or restore.
- After `e2fsck` exits, p10 remains released until the operator power-cycles.
  **Reboot is required to restore p10 RO.** Do not boot Android before that.

## Validated prerequisite

The original p10 backup was independently rehashed:

- 30,334,779,392 bytes
- SHA256 `c637b516529dbee491bc3d435ffcf451527ef9902d3cad8035e4fc6437133579`

The repaired host copy was rehashed and its fsck passed:

- SHA256 `9c0826d8d98c77c785c7829388167955481e48f4778b85576233824ed17a375f`
- read-only e2fsck all five phases, exit 0

The tablet remains unrepaired.

## Operator protocol

Do not proceed without the verified backup above and a separate explicit
authorization for the physical write.

```sh
fastboot flash boot artifacts/offline98-repair-ready/wingray-offline98-repair.img
fastboot reboot
```

Then use a raw serial terminal, not the framing capture tool:

```sh
picocom -b 115200 /dev/ttyACM0
```

Read-only preflight (p10 stays RO; no write):

```text
PREFLIGHT_P10 <32-hex-nonce>
```

Arm the write gate:

```text
REPAIR_P10 <same-nonce>
```

The device replies `XOOM_REPAIR_P10_ARMED`. Confirm with:

```text
REPAIR_P10_CONFIRM <same-nonce>
```

Then `/bin/p10-repair`:

1. verifies p10 is initially RO;
2. runs the fixed policy helper to release p10 only;
3. verifies p10 is RW and p9, p8, whole disk are still RO;
4. refuses if `/data` or `/cache` is mounted;
5. runs interactive `e2fsck -f /dev/mmcblk0p10`;
6. syncs and reports `XOOM_REPAIR_E2FSCK_EXIT <code>`;
7. holds without relocking p10.

The operator answers the e2fsck prompts manually. There is no `-y`, `-p`,
automatic repair, automatic restore or automatic reboot.

After e2fsck exits:

1. power-cycle the tablet;
2. boot the read-only inspect image;
3. verify p10/p9/whole disk are RO and ext4/no-crypto/ro-mount still pass;
4. capture full read-only evidence;
5. do not boot Android or Stage B/C.

## Limits

The standalone e2fsck has passed hardware RAM-fixture tests, but this repair
image and the interactive release path have **not** been hardware-tested.
The only valid source is the verified original p10. The repaired host image is
not to be restored by this gate. No cache repair is provided.
