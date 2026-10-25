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
 *) echo 'Only the corrected fbmap profile can be packaged.' >&2; exit 1;;
esac
make "${args[@]}" "$defconfig"
# Kconfig orders NETDEVICES before the NET symbol in this tree; force the
# Wi-Fi dependency set after the initial defconfig and resolve it cleanly.
"$build/source/scripts/config" --file "$build/out/.config" \
 --enable NETDEVICES --enable WLAN --enable MODULES --enable MODULE_UNLOAD \
 --enable CFG80211 --enable WIRELESS_EXT --enable WEXT_CORE --enable WEXT_PROC --enable WEXT_PRIV \
 --module LEGACY_BCMDHD --disable BCM4330 --disable BROADCOM_WIFI --disable BRCMFMAC --disable BRCMFMAC_SDIO
make "${args[@]}" olddefconfig
cp "$build/out/.config" "$dest/kernel.config"
for helper in build-android44-probe build-display-pattern build-touch-events build-cpu-handoff-probe; do
 XOOM_BUILD_ROOT="$build" XOOM_ARTIFACT_DIR="$dest" bash "$root/scripts/$helper.sh"
done
make "${args[@]}" -j"${JOBS:-4}" modules
mkdir -p "$dest/modules"
cp "$build/out/drivers/net/wireless/bcmdhd-legacy/bcmdhd.ko" "$dest/modules/bcmdhd.ko"
"$build/toolchain/bin/arm-linux-androideabi-strip" --strip-debug "$dest/modules/bcmdhd.ko"
python3 "$root/scripts/prepare-android-gpu.py" --runtime-dir "$dest" --archive "$dest/runtime-source.cpio"
cp "$dest/runtime-source.cpio" "$build/out/usr/wingray-android-runtime.cpio"
make "${args[@]}" -j"${JOBS:-4}" zImage-dtb
make "${args[@]}" tegra20-motorola-wingray-gpu-test.dtb tegra20-motorola-wingray-android44-smp2.dtb
cp "$build/out/arch/arm/boot/"{zImage,zImage-dtb} "$dest/"
cp "$build/out/arch/arm/boot/dts/$dt.dtb" "$build/out/arch/arm/boot/dts/"tegra20-motorola-wingray-{gpu-test,android44-smp2}.dtb "$dest/"
cp "$build/out/System.map" "$dest/"
cp "$build/out/usr/initramfs_data.cpio.gz" "$dest/builtin-initramfs.cpio.gz"
python3 "$root/scripts/pack-android-gpu-image.py" --kernel-dir "$dest" --output-dir "${XOOM_IMAGE_DIR:?Set a new ignored image directory}"
echo "Build complete; no device operations. Build: $build Artifacts: $dest"
