# CPU-frequency change — preservation evidence and limits

## Confirmed from the hardware report

- SMP: `SMP: Total of 2 processors activated`.
- CPU1 online and reports its own cpufreq interface.
- Shared policy: `policy0` covers CPUs 0 and 1.
- Android booted; SurfaceFlinger, zygote, servicemanager, vold and netd running.
- Persistent p10 `/data` mounted; user data path unchanged.
- Wi-Fi stack loaded (`wpa_supplicant`, bcmdhd firmware path).
- CPCAP core probed normally.
- GPU fixed-clock profile remained enabled together with cpufreq.

## Not re-tested in this run

- CPU1 offline/online hotplug cycle.
- GPU render benchmark.
- Wi-Fi association and Bluetooth pairing.
- CPCAP power-button event.
- LP2 suspend/resume.

No code was changed in SMP, hotplug, GPU, Wi-Fi, Bluetooth, storage, CPCAP
power handling, or LP2. The only behavioural change is cpufreq registration and
the GPU-conditional suppression of cpufreq EMC votes.

The shared policy and performance governor keep the CPU at the existing 1 GHz
clock; no voltage transition or dynamic frequency change occurred.
