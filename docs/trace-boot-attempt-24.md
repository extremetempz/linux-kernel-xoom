# Image 24: fresh checksummed diagnostics and eMMC/BigPart gate

Prepared 21 October 2026. See [the staged plan](next-porting-stage.md) for the
architecture decision, acceptance criteria and next branches.

The hardware-tested kernel, DT and configuration are reused byte-for-byte from
candidate 23. There is no new kernel revision, driver modification or trace
cookie: it remains `0x584d0017`. Only the RAM diagnostic changes. Fresh USB
request nonces distinguish reports; this cycle does not retrieve reserved RAM.

The previous cached report/interactive shell is replaced by a fixed `PING` /
`REPORT` service. Before reading requests it configures raw/no-echo terminal
mode, sends no unsolicited report, and never evaluates USB input as shell code.
Each fresh report waits at most 20 seconds for all ten partitions, captures
current metadata and logs, and is sent as base64 with nonce, length and SHA-256.
The host validates every field before accepting evidence. A failed integrity
check or missing disk remains explicit and does not become a successful gate.
Only virtual filesystems are mounted; no Android partition is mounted and no
block write or regulator/clock configuration command is exposed.

## Offline validation

Nine local tests cover:

- Arbitrary fragmentation, stale identity, missing completion, oversized input,
  malformed encoding, wrong byte count, wrong checksum, disconnect and timeout.
- The actual server script over a pseudo-terminal: silence before request,
  readiness, rejected arbitrary/invalid commands, successive fresh reports and
  over-limit response rejection.
- The actual report script with controlled proc/sys/clock dependencies: bounded
  missing-disk wait, fresh uptime after a second request, and exact geometry.
- Complete-reference matching, missing partitions, differing geometry, capacity,
  overlapping extents, duplicate records and nonvirtual mount rejection.

These use host BusyBox 1.36.1 and simulated terminal/proc/sys dependencies. They
do not prove ARM BusyBox 1.31 behavior, physical USB transport or storage.
The target uses the same pinned standalone ARMv5T runtime already tested in
candidate 23. Its hash is unchanged. Actual BigPart source tests, including
1000 capacities, pass. The legacy mode reproduces image 23 byte-for-byte.

The new image passes the boot-layout audit and is SHA-256:
`68ed529e11daa7870bbe6c63b8dde8452f608007857e7f60fc221046924167b1`.
The kernel component equals the tested candidate-23 component exactly.

## Test scope

Before flashing, identify the exact Xoom, wall power and boot completion, compare
full live boot/recovery partitions to the originals, and save a fresh disk
capacity plus all ten partition extents from the working Android kernel.
Compare the new kernel against that live BigPart view, not the raw legacy GPT.

Flash boot only. Connect the new gadget to VMware and grant temporary per-node
serial access if required. Obtain two separately requested, checksum-verified
reports across close/reopen. Inspect current kernel/MMC logs and compare capacity,
all partition extents and virtual-only mounts. A mismatch forbids progressing
to Android filesystem mounts. Restore original boot and verify both complete
original images. No reserved-RAM snapshot is requested for this cycle.

## Physical result: transport and partitions confirmed; capacity discrepancy

Two separately requested reports across serial-port close/reopen passed nonce,
length, SHA-256 and completion validation. Each contained 36,073 bytes with
fresh uptimes (approximately 119 and 165 seconds). Storage wait was zero.
Only virtual filesystems were mounted. The card had appeared at 0.695 seconds;
the earlier cached report was too early to establish absence of eMMC.

All ten partition start/size pairs match the fresh working-kernel BigPart view.
However the disk reports **62,513,152 sectors**, while the original kernel
reports **62,521,344**: 8,192 sectors / 4 MiB fewer. The host correctly reports
`disk_capacity_mismatch`; the storage gate is not passed. No Android filesystem
was mounted and no on-disk GPT was changed.

Source review establishes that the donor subtracts `EXT_CSD_BOOT_MULT * 512`
from large nonremovable cards' raw sector count. The working 2.6.39 MMC decode
uses the raw count. The observed difference equals both exposed 2 MiB boot
areas combined. This strongly supports that subtraction as the capacity cause;
raw EXT_CSD was not separately captured in this cycle. Image 25 tests a scoped
correction rather than claiming a hardware fix from source review alone.

The existing Wingray/controller-gated GPT fallback can read the bootloader's
relocated GPT at sector 62,513,151 without reducing apparent disk capacity.
Header CRC and entry validation remain enabled; no GPT repair is proposed.

Original boot was restored. Complete boot and recovery readbacks match their
preserved originals, Android boot completed and its boot ID remained stable
through verification. No reserved-RAM mapping was performed. Android startup
under Linux 4.4 and other peripherals remain unverified.
