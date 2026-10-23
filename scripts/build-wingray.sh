#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/sources/kernel-donor"
profile="${XOOM_PROFILE:-peripherals}"
case "$profile" in
  peripherals) defconfig=wingray_bringup_defconfig; dtname=tegra20-motorola-wingray; default_dest="$root/artifacts/wingray44";;
  early) defconfig=wingray_early_defconfig; dtname=tegra20-motorola-wingray-early; default_dest="$root/artifacts/wingray-early";;
  trace) defconfig=wingray_trace_defconfig; dtname=tegra20-motorola-wingray-early; default_dest="$root/artifacts/wingray-trace";;
  android44) defconfig=wingray_android44_defconfig; dtname=tegra20-motorola-wingray-android44; default_dest="$root/artifacts/wingray-android44";;
  android44-touch) defconfig=wingray_android44_touch_defconfig; dtname=tegra20-motorola-wingray-android44-touch; default_dest="$root/artifacts/wingray-android44-touch";;
  android44-l2) defconfig=wingray_android44_l2_defconfig; dtname=tegra20-motorola-wingray-android44-l2; default_dest="$root/artifacts/wingray-android44-l2";;
  android44-smp) defconfig=wingray_android44_smp_defconfig; dtname=tegra20-motorola-wingray-android44-smp; default_dest="$root/artifacts/wingray-android44-smp";;
  android44-smp2) defconfig=wingray_android44_smp2_defconfig; dtname=tegra20-motorola-wingray-android44-smp2; default_dest="$root/artifacts/wingray-android44-smp2";;
  android44-smptrace) defconfig=wingray_android44_smptrace_defconfig; dtname=tegra20-motorola-wingray-android44-smptrace; default_dest="$root/artifacts/wingray-android44-smptrace";;
  display) defconfig=wingray_display_defconfig; dtname=tegra20-motorola-wingray-display; default_dest="$root/artifacts/wingray-display";;
  panelbus) defconfig=wingray_panelbus_defconfig; dtname=tegra20-motorola-wingray-panelbus; default_dest="$root/artifacts/wingray-panelbus";;
  diagnostic) defconfig=wingray_diagnostic_defconfig; dtname=tegra20-motorola-wingray-diagnostic; default_dest="$root/artifacts/wingray-diagnostic";;
  *) echo 'XOOM_PROFILE must be peripherals, early, trace, diagnostic, panelbus, display, android44, android44-touch, android44-l2 android44-smp, android44-smp2 or android44-smptrace.' >&2; exit 1;;
esac
dest="${XOOM_ARTIFACT_DIR:-$default_dest}"
toolchain="${XOOM_TOOLCHAIN_DIR:-$root/toolchains/android-gcc49}"
build="${XOOM_BUILD_ROOT:-$(mktemp -d /tmp/xoom-wingray44.XXXXXX)}"
case "$build" in *' '*|*:* ) echo 'XOOM_BUILD_ROOT must not contain spaces or colons.' >&2; exit 1;; esac
test -f "$src/arch/arm/configs/wingray_bringup_defconfig" || {
  echo 'Fetch sources and apply kernel patches first.' >&2; exit 1;
}
test -x "$toolchain/bin/arm-linux-androideabi-gcc" || {
  echo 'Run bash scripts/setup-toolchain.sh first.' >&2; exit 1;
}
# Linux 4.4 makefiles reject paths containing spaces. Keep the checkout in
# the user's workspace and compile a mirror in a dedicated temporary folder.
mkdir -p "$build/source" "$build/toolchain" "$build/out" "$dest"
rsync -a --exclude=.git "$src/" "$build/source/"
rsync -a "$toolchain/" "$build/toolchain/"
export KBUILD_BUILD_TIMESTAMP='2026-10-18 00:00:00 +0000'
export KBUILD_BUILD_USER=xoom
export KBUILD_BUILD_HOST=builder
export KBUILD_BUILD_VERSION=1
args=(-C "$build/source" O="$build/out" ARCH=arm
  CROSS_COMPILE="$build/toolchain/bin/arm-linux-androideabi-"
  KCFLAGS='-fno-unwind-tables -fno-asynchronous-unwind-tables')
make "${args[@]}" "$defconfig"
make "${args[@]}" -j"${JOBS:-4}" zImage-dtb
cp "$build/out/arch/arm/boot/zImage" "$build/out/arch/arm/boot/zImage-dtb" "$dest/"
cp "$build/out/arch/arm/boot/dts/$dtname.dtb" "$dest/"
cp "$build/out/.config" "$dest/kernel.config"
cp "$build/out/System.map" "$dest/"
(cd "$dest" && sha256sum zImage zImage-dtb "$dtname.dtb" kernel.config System.map > SHA256SUMS)
python3 "$root/scripts/verify-kernel.py" "$dest" "$profile"
printf 'Build directory: %s\nArtifacts: %s\n' "$build" "$dest"
echo 'Experimental bring-up kernel only; this is not a flashable boot image.'
