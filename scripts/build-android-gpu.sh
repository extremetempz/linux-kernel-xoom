#!/usr/bin/env bash
# Separate combined profile; never accesses a device or overwrites evidence.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build="${XOOM_BUILD_ROOT:-$(mktemp -d /tmp/xoom-android-gpu.XXXXXX)}"
dest="${XOOM_ARTIFACT_DIR:?Set a new ignored artifact directory}"
case "$build" in *' '*|*:*) echo 'Build path must contain no spaces/colons.' >&2; exit 1;; esac
[ ! -e "$dest" ] || { echo 'Use a new artifact directory.' >&2; exit 1; }
[ -z "$(git -C "$root/sources/kernel-donor" status --porcelain)" ] || { echo 'Commit the kernel source before building.' >&2; exit 1; }
mkdir -p "$build/source" "$build/toolchain" "$build/out/usr" "$dest"
rsync -a --exclude=.git "$root/sources/kernel-donor/" "$build/source/"
rsync -a "$root/toolchains/android-gcc49/" "$build/toolchain/"
python3 - "$root" "$build/out/usr/wingray-android-runtime.cpio" <<'PY'
from pathlib import Path
import sys
sys.path.insert(0,str(Path(sys.argv[1])/'scripts'))
from android44_image import pack_newc
Path(sys.argv[2]).write_bytes(pack_newc({}))
PY
export KBUILD_BUILD_TIMESTAMP='2026-10-18 00:00:00 +0000'
export KBUILD_BUILD_USER=xoom KBUILD_BUILD_HOST=builder KBUILD_BUILD_VERSION=1
args=(-C "$build/source" O="$build/out" ARCH=arm CROSS_COMPILE="$build/toolchain/bin/arm-linux-androideabi-" KCFLAGS='-fno-unwind-tables -fno-asynchronous-unwind-tables')
case "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" in
 fbmap) defconfig=wingray_android44_gpu_fbmap_defconfig; dt=tegra20-motorola-wingray-android44-gpu-fbmap;;
 bluetooth) defconfig=wingray_android44_bluetooth_defconfig; dt=tegra20-motorola-wingray-android44-bluetooth;;
 battery) defconfig=wingray_android44_battery_defconfig; dt=tegra20-motorola-wingray-android44-battery;;
 displaypm) defconfig=wingray_android44_displaypm_defconfig; dt=tegra20-motorola-wingray-android44-displaypm;;
 displaydc) defconfig=wingray_android44_displaydc_defconfig; dt=tegra20-motorola-wingray-android44-displaypm;;
 wakeirq) defconfig=wingray_android44_wakeirq_defconfig; dt=tegra20-motorola-wingray-android44-wakeirq;;
 wakeirqbl) defconfig=wingray_android44_wakeirqbl_defconfig; dt=tegra20-motorola-wingray-android44-wakeirq;;
 wakeirqtrace) defconfig=wingray_android44_wakeirqtrace_defconfig; dt=tegra20-motorola-wingray-android44-wakeirqtrace;;
 *) echo 'Choose fbmap, bluetooth, battery, displaypm, displaydc, wakeirq, wakeirqbl or wakeirqtrace.' >&2; exit 1;;
esac
make "${args[@]}" "$defconfig"
# Kconfig orders NETDEVICES before the NET symbol in this tree; force the
# Wi-Fi dependency set after the initial defconfig and resolve it cleanly.
"$build/source/scripts/config" --file "$build/out/.config" \
 --enable NETDEVICES --enable WLAN --enable MODULES --enable MODULE_UNLOAD \
 --enable CFG80211 --enable WIRELESS_EXT --enable PACKET --disable RD_GZIP --disable RD_BZIP2 --disable RD_LZMA --disable RD_LZO --disable RD_LZ4 --enable RD_XZ --enable WEXT_CORE --enable WEXT_PROC --enable WEXT_PRIV \
 --enable BROADCOM_WIFI --disable BCM4330 --disable BRCMFMAC --disable BRCMFMAC_SDIO
make "${args[@]}" olddefconfig
# A missing exported patch must not silently build a different experiment.
case "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" in
 displaydc|wakeirq)
  grep -qx 'CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y' "$build/out/.config" || { echo 'Apply patch 0151 to the donor first.' >&2; exit 1; };;
esac
if [[ "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = wakeirq || "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = wakeirqbl || "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = wakeirqtrace ]]; then
 grep -qx 'CONFIG_MFD_CPCAP_WINGRAY_IRQ_TEST=y' "$build/out/.config" || { echo 'Apply patch 0152 to the donor first.' >&2; exit 1; }
 ! grep -qx 'CONFIG_SUSPEND=y' "$build/out/.config" || { echo 'Wake IRQ test must remain awake-only.' >&2; exit 1; }
 if [[ "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = wakeirqbl || "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = wakeirqtrace ]]; then
  ! grep -qx 'CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y' "$build/out/.config" || { echo 'wakeirqbl must not enable DC resume.' >&2; exit 1; }
 fi
fi
cp "$build/out/.config" "$dest/kernel.config"
for helper in build-android44-probe build-display-pattern build-touch-events build-cpu-handoff-probe; do
 XOOM_BUILD_ROOT="$build" XOOM_ARTIFACT_DIR="$dest" bash "$root/scripts/$helper.sh"
done
if [[ "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = displaypm || "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = displaydc || "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = wakeirq || "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = wakeirqbl || "${XOOM_ANDROID_GPU_PROFILE:-fbmap}" = wakeirqtrace ]]; then
 XOOM_BUILD_ROOT="$build" XOOM_ARTIFACT_DIR="$dest" bash "$root/scripts/build-display-lights.sh"
fi
make "${args[@]}" -j"${JOBS:-4}" modules
mkdir -p "$dest/modules"
cp "$build/out/drivers/net/wireless/bcmdhd/bcmdhd.ko" "$dest/modules/bcmdhd.ko"
"$build/toolchain/bin/arm-linux-androideabi-strip" --strip-debug "$dest/modules/bcmdhd.ko"
python3 "$root/scripts/prepare-android-gpu.py" --runtime-dir "$dest" --archive "$dest/runtime-source.cpio"
cp "$dest/runtime-source.cpio" "$build/out/usr/wingray-android-runtime.cpio"
make "${args[@]}" -j"${JOBS:-4}" zImage-dtb
make "${args[@]}" tegra20-motorola-wingray-android44-wakeirq.dtb tegra20-motorola-wingray-android44-displaypm.dtb tegra20-motorola-wingray-android44-battery.dtb tegra20-motorola-wingray-android44-bluetooth.dtb tegra20-motorola-wingray-gpu-test.dtb tegra20-motorola-wingray-android44-smp2.dtb tegra20-motorola-wingray-android44-gpu-fbmap.dtb
cp "$build/out/arch/arm/boot/"{zImage,zImage-dtb} "$dest/"
cp "$build/out/arch/arm/boot/dts/$dt.dtb" "$build/out/arch/arm/boot/dts/"tegra20-motorola-wingray-{gpu-test,android44-smp2}.dtb "$dest/"
cp "$build/out/arch/arm/boot/dts/tegra20-motorola-wingray-android44-gpu-fbmap.dtb" "$dest/"
cp "$build/out/arch/arm/boot/dts/tegra20-motorola-wingray-android44-bluetooth.dtb" "$build/out/arch/arm/boot/dts/tegra20-motorola-wingray-android44-battery.dtb" "$dest/"
cp "$build/out/arch/arm/boot/dts/tegra20-motorola-wingray-android44-displaypm.dtb" "$dest/"
cp "$build/out/arch/arm/boot/dts/tegra20-motorola-wingray-android44-wakeirq.dtb" "$dest/"
cp "$build/out/System.map" "$dest/"
for f in "$build/out/usr/initramfs_data.cpio.xz" "$build/out/usr/initramfs_data.cpio.lz4" "$build/out/usr/initramfs_data.cpio.gz"; do
  [ ! -f "$f" ] || { cp "$f" "$dest/builtin-initramfs.cpio.${f##*.}"; break; }
done
# The image validator expects the canonical gzip copy even when the kernel
# carries an XZ-compressed built-in initramfs.
if [ -f "$dest/builtin-initramfs.cpio.xz" ]; then
  xz -dc "$dest/builtin-initramfs.cpio.xz" | gzip -9 > "$dest/builtin-initramfs.cpio.gz"
fi
python3 "$root/scripts/pack-android-gpu-image.py" --kernel-dir "$dest" --output-dir "${XOOM_IMAGE_DIR:?Set a new ignored image directory}"
echo "Build complete; no device operations. Build: $build Artifacts: $dest"
