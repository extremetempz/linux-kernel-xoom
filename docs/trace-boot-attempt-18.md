# Candidate 18: first PID 1 userspace page fault

Built and physically tested 20 October 2026. The first observed PID 1 page
fault is a Thumb instruction at `0xb6f12996` accessing address `0x90`, followed
by PID 1's SIGSEGV and an init-death panic. The original images are restored
and verified; Android is running. This candidate did not boot Android.

## Purpose and limits

Candidate 17 established an init-death panic with wait status `0xb` (SIGSEGV)
after exec succeeded. Its exact prepared executable, linker and library
closure ran successfully in a temporary isolated root on the restored
working kernel. The faulting userspace instruction/address remain unknown.

Patch 0028 records the first ARM userspace page fault observed for global
PID 1, immediately before signal delivery. It stores PC, fault address, FSR,
CPSR, signal and signal code. These replace the seven entry-register words
at offsets `0x0c..0x24`, publishing tag `USF1` last. The later `XIT1` exit
status record remains independent. The physical record stays 128 bytes;
the bounded reader and its single-page read-only mapping are unchanged.

The guard requires Wingray's persistent mapping-ready flag, matching magic,
format and build cookie, and no previous fatal event or user-fault record.
It performs no allocation, locking, DT walk or user-memory read. The caller
limits this to PID 1. A userspace signal handler could recover, so this is
the first observed page fault, not proof by itself that it caused death.

Patch 0029 changes only the build cookie to `0x584d0012`. Runtime files,
hardware configuration and memory sizing are unchanged from candidate 17;
no speculative userspace or peripheral fix is bundled into this test.

## Validation and recovery

The diagnostic kernel and appended DTB pass build/config/image validation.
Ten cases execute the actual compiled user-fault helper, with init memory
inaccessible, checking ARM/Thumb status, signed signal code, readiness and
header guards, bounded writes, first-record/fatal preservation, signature
ordering and coexistence with a subsequent init-exit record. Existing init
exec, init-exit, panic-prefix, decoder and memory-limit regressions pass.
The committed patch series is recognized in a clean donor checkout.

Preflight readbacks match both complete original images. Android completed
boot before the test, with AC power connected and battery at 70%. Only boot
is written for the authorized test. The original boot must be restored and
both preserved images verified before the single bounded trace retrieval.
Android partitions stay unmounted throughout the diagnostic.

## Physical trace and interpretation

The single bounded snapshot has valid format 2 and fresh cookie `0x584d0012`.
`USF1` records PC `0xb6f12996`, address `0x90`, FSR `0x5`, CPSR
`0x20000030` (Thumb userspace), signal 11 and kernel signal-code word
`0x00030001` (`__SI_FAULT | SEGV_MAPERR` in this build). Independent `XIT1`
records wait status `0xb`, without a core flag. Phase remains `0x421`
(`init_exec_succeeded`); the first fatal marker is panic.

This identifies an access to an unmapped low address in userspace, then
PID 1 death. It is consistent with a null-related pointer, but the address
alone does not identify the source pointer or its cause. The captured
runtime PC has not been assigned to an executable/library mapping. Do not
subtract a guessed ASLR base or present a guessed function as established.
The next useful instrumentation is its actual executable mapping/file
offset and a few argument registers or a separately controlled static init.

No expected USB serial gadget/report reached this VMware guest during the
observation. Runtime USB PHY/UDC probe success is still unverified. Only
boot was flashed, then the original was restored. Complete boot/recovery
readbacks match their preserved images. Initial retrieval stopped at device
readiness before any trace mapping because the normal ADB USB device was
not yet reconnected. After reconnection, exactly one bounded snapshot was
retrieved; Android retained its boot ID and no new kernel fault appeared.

## Subsequent runtime-environment control

The earlier isolated-root success inherited the ADB shell's environment.
Clearing that environment caused even the `true` applet to terminate with
status 139 under the working kernel. To exclude a BusyBox `env`-applet bug,
three tiny static ARM launchers used raw `execve`, without libc or a dynamic
interpreter, to start the exact copied BusyBox shell. Inherited environment
succeeded and printed the control marker. Empty environment, and an
environment containing only the kernel's `HOME=/` and `TERM=linux`, both
terminated with status 139 before printing. The working Android boot ID
remained unchanged, and the temporary roots were removed after each control.

This establishes a startup-environment sensitivity in the diagnostic runtime
under the working kernel too. It does not yet establish the same faulting
PC as candidate 18 or identify the required variable. Environment isolation
is now a better next step than another hardware flash or speculative driver
change. One minimization run lost USB during file copy, before its matrix;
the partial root was subsequently inventoried, hash-checked and removed.
No original partition was written by these controls.

After reconnection, a raw-exec minimization reduced the successful
environment from 21 variables to just `ANDROID_PROPERTY_WORKSPACE`; empty
environment still exited 139. This identifies the inherited property
workspace context as a requirement of this copied runtime in the control.
It does not prove that the same instruction faulted in the control, and it
does not establish that setting a variable alone supplies a valid property
area/file descriptor in a standalone initramfs.

The official static ARMv5T BusyBox replacement then passed raw-exec controls
with inherited, empty and kernel-like environments on the working kernel,
without copying an Android linker or library. Its ELF has no interpreter or
shared-library dependency, ARMv5T/VFPv2 attributes and no NEON attribute.
Candidate 19 changes the diagnostic runtime and fresh cookie, retaining the
hardware settings. Static runtime provenance and its pinned hash are in
`scripts/fetch-diagnostic-runtime.py`; `tests/runtime-exec-probe.S` contains
the independent raw-exec control source.
