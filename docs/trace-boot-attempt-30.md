# Image 30 physical test — Android init and SystemServer reached

Tested 22 October 2026 with the explicitly authorized boot-only flash cycle.
**This advanced into Android userspace, but did not complete Android boot or
show a verified lockscreen.** Original boot and recovery were fully verified
after restoration; the working ROM returned. No recovery or partition-layout
write occurred.

Image SHA-256:
`a5b16f0ca7ac80a3d232e8ca4f5fc059fcc9fbac0a71c16d5a3d10d8c274c93d`.
Kernel source: `400dbc8e`, Linux `4.4.147-wingray-android44`, cookie `0x584d001e`.
Both local preserved originals and complete live pre/post readbacks matched.
Wall power was connected and battery was 100% before testing.

## Verified physical results

Two independently nonce-correlated length/SHA-verified USB reports:

| Report | Bytes | SHA-256 |
|---|---:|---|
| 1 | 97,614 | `9c57fd64843b6d47a4a7dbee14e8f098111696863dc0d735131f3ac9204e0a4a` |
| 2 | 121,619 | `375ccc03197b214568785cf3fdd01cc9ca9fa179ac78a73b25c5ceb3e42d109b` |

Both reports passed the explicit Android read-only mount/geometry policy:
62521344 sectors, all ten BigPart extents, all eleven eMMC RO flags, fixed p8
system with journal replay disabled, RAM data/cache and read-only RAM graphics
overlays. All thirteen fixed installed-system SHA-256 references matched.

The target ABI probe exited 0. Write opens were rejected on all eleven fixed
block paths; NULL raw-MMC/BLKROSET requests were rejected before decoding. No
real block write or valid raw command was attempted. Binder version 7, logger
v1/v2, private ashmem and UNIX/uevent sockets passed on the Xoom.

The bootstrap passed every stage and executed original Android init as PID 1.
Reports showed original ueventd, service manager, SurfaceFlinger, zygote,
SystemServer and other retained Android services. Android properties reported
4.4.4 and hardware stingray. This establishes process execution, not stable
framework completion or proof of displayed software-rendered Android UI.

## Located stop

SystemServer repeatedly aborted with SIGABRT. Backtraces include
`EventHub::EventHub()+184` in the installed `libinputservice.so`. The crash-stack
words reconstruct the assertion:

> Could not register INotify for /dev/input. errno=2

The exact assertion is present in tagged
[AOSP 4.4 EventHub.cpp](https://android.googlesource.com/platform/frameworks/base/+/android-4.4.4_r2/services/input/EventHub.cpp).
Its constructor watches `/dev/input` and treats a failed watch as fatal. The
same source accepts an empty directory and creates its virtual keyboard
internally; `/dev/uinput` or fabricated event nodes are not required for this
specific step.

The isolated kernel intentionally has input drivers disabled. Original Android
init replaces bootstrap `/dev` with a fresh tmpfs, and no input devices caused
ueventd to populate that path. The next correction creates the directory in
Android's own `on init` action, after that replacement and before zygote starts.
A host test reproduces ENOENT with real inotify, then succeeds on an empty
ordinary temporary directory using the generated init rule. The hardware test
of that correction is a separate image, not a result claimed here.

Neither report had `sys.boot_completed=1`. The operator said it got further but
did not identify a specific screen, so no visual Android milestone is claimed.
There was no observed SIGILL in this failure, but unexercised library paths,
touch, provisioning and completed framework boot remain unverified.

Raw USB reports, tombstones, crash-stack reconstruction and complete readbacks
remain private under ignored `artifacts/android44-image-30-ready/`.
