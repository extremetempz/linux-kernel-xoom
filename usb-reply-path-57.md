# USB reply-path investigation — image 57

## Verified evidence and scope

Build 56 received a recognized request with a valid nonce (`reporter_stage=3`), but its host capture saved zero response bytes and timed out in readiness negotiation. The GPU release tool was never run. That evidence does not locate the missing reply or demonstrate a rendering failure. See `gpu-render-test-56-result.md` for the retained record and restoration checks.

The checked-in Linux 4.4 gadget source has a relevant observability gap:

- `drivers/usb/gadget/function/u_serial.c:gs_write()` returns the count accepted into its software buffer. It calls `gs_start_tx()` but does not return that function's status.
- `gs_start_tx()` calls `usb_ep_queue()`. On failure it returns the request to the pool and breaks out. A successful userspace write therefore does not prove packet queuing, USB completion or host delivery.
- The reporter records its parser checkpoint before running the external BusyBox readiness `printf`. Build 56 has no checkpoint after that command.
- Host readiness requires a newline-terminated, matching-nonce `XOOM_READY_V2` line. Its raw serial configuration and bounded parser are unchanged by this diagnostic.

These are source observations, not proof that endpoint queuing failed on the Xoom. There is currently no evidence sufficient to justify a functional USB-driver fix.

## Separate diagnostic changes

Patch 0108 adds profile `wingray_gpu_usb_reply_defconfig`, fresh cookie `0x584d0057`, and three fixed privileged trace commands. Existing profiles and artifacts remain intact. The commands write only the existing retained USB-stage slot; no selectable address or offset is exposed.

| Command / USB stage | Meaning |
| --- | --- |
| D / 3 | About to execute the readiness printf |
| E / 4 | That command returned success |
| F / 5 | That command returned failure |

Parser A/B/C checkpoints continue to use the separate reporter slot. Subsequent parser progress cannot erase the USB reply result. A subsequent readiness write can replace E/F with D; this identifies the most recent attempted reply, not a cumulative history. The preexisting `usb_result` field is not a captured printf errno.

The image packer enables this bracket only for 57. The runtime and kernel retain the same initialization, GPU gate, clocks, regulators, submission implementation and USB framing. No GPU release is part of the USB diagnosis. The existing release tool accepts only build 56 and cannot release 57; any future rendering test requires an explicit reviewed tool update after a fresh baseline succeeds.

## Validation and limits

The packed server is exercised on a real host PTY using the actual host readiness handshake. Successful output records D then E. A closed-output-descriptor control makes the real printf fail and records D then F. Neither creates the GPU-release file. Existing gate controls still pass. These controls exercise host BusyBox/PTY behavior, not the ARM gadget hardware.

The compiled retained helper tests cover scalar and vectored fixed commands, privilege checks, short/bad copies, stale headers, fixed offsets, and independent USB-slot decoding. Linked-image checks separately verify the actual embedded archive and compressed kernel payload. Hardware evidence is still needed.

## Staged hardware test and interpretation

1. Publish the diagnostic source before flashing, then refresh battery/power, original boot/recovery full hashes, device identity and candidate digest. Save a fresh private test state. Flash boot only; preserve recovery, all partition layouts and build 56.
2. Connect the gadget to VMware, grant the temporary serial permission, and capture one bounded PING/REPORT exchange. Do not run GPU_RUN or change clocks. Record host wire bytes and exact errors.
3. If readiness fails, return to fastboot, restore the verified original, confirm normal Android and both full partition hashes, then retrieve the fresh-cookie retained record using the guarded single-read procedure. Never reuse build 56's completed mapping attempt.
4. D without E/F locates the last checkpoint before command completion, but could also reflect process termination/reset or a failed trace write; it is not by itself proof of a blocked tty write. F directs the next investigation to the local command/write failure and RAM error log. E with zero host bytes directs the next instrumentation toward gadget queue/completion and host/VM receive state. E still does not establish delivery.
5. Only after a fresh verified full report should GPU rendering be reconsidered. Do not combine a transport repair with GPU functional changes.

No device operation or hardware success is implied by this preparation document.

## Prepared artifact

Image 57 compiled successfully and passed configuration/DT/symbol checks, packed-image and ARM dependency checks, linked built-in archive and compressed payload checks, and ARM reset/retained-trace guard checks. This is not hardware validation.

- Image: `artifacts/gpu-render57-ready/wingray-gpu-render-diagnostic.img`
- Size: 5797888 bytes
- SHA-256: `ac2267bd05b370bb3866d53cf725605c05999c8c3e5fccdd3d30394139126a5c`
- Kernel source commit: `87db9dbd`
- Flash status: not flashed during preparation.
