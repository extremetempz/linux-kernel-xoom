#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/sources/kernel-donor"
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
mkdir -p "$build/source" "$build/toolchain" "$build/out" "$root/artifacts/wingray44"
rsync -a --exclude=.git "$src/" "$build/source/"
rsync -a "$toolchain/" "$build/toolchain/"
export KBUILD_BUILD_TIMESTAMP='2026-10-18 00:00:00 +0000'
export KBUILD_BUILD_USER=xoom
export KBUILD_BUILD_HOST=builder
export KBUILD_BUILD_VERSION=1
args=(-C "$build/source" O="$build/out" ARCH=arm
  CROSS_COMPILE="$build/toolchain/bin/arm-linux-androideabi-"
  KCFLAGS='-fno-unwind-tables -fno-asynchronous-unwind-tables')
make "${args[@]}" wingray_bringup_defconfig
make "${args[@]}" -j"${JOBS:-4}" zImage-dtb
dest="$root/artifacts/wingray44"
cp "$build/out/arch/arm/boot/zImage" "$build/out/arch/arm/boot/zImage-dtb" "$dest/"
cp "$build/out/arch/arm/boot/dts/tegra20-motorola-wingray.dtb" "$dest/"
cp "$build/out/.config" "$dest/kernel.config"
cp "$build/out/System.map" "$dest/"
(cd "$dest" && sha256sum zImage zImage-dtb tegra20-motorola-wingray.dtb kernel.config System.map > SHA256SUMS)
python3 "$root/scripts/verify-kernel.py" "$dest"
printf 'Build directory: %s\nArtifacts: %s\n' "$build" "$dest"
echo 'Experimental bring-up kernel only; this is not a flashable boot image.'
