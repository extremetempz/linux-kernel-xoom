#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/sources/kernel-baseline"
out="$root/out/baseline"
: "${CROSS_COMPILE:?Set CROSS_COMPILE to the ARM toolchain prefix}"
command -v "${CROSS_COMPILE}gcc" >/dev/null
test -f "$src/arch/arm/configs/stingray_defconfig" || {
  echo 'Baseline defconfig missing: fetch sources and inspect upstream first.' >&2
  exit 1
}
mkdir -p "$out"
make -C "$src" O="$out" ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" stingray_defconfig
make -C "$src" O="$out" ARCH=arm CROSS_COMPILE="$CROSS_COMPILE" -j"${JOBS:-2}" zImage modules
echo "Kernel output: $out/arch/arm/boot/zImage (not a flashable boot image)"
