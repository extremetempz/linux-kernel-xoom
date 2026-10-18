#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
prefix="$root/toolchains/android-gcc49/bin/arm-linux-androideabi-"
dest="${XOOM_READER_OUTPUT:-$root/artifacts/trace-reader}"
mkdir -p "$dest"
"${prefix}gcc" -march=armv7-a -marm -mfloat-abi=soft -O2 -Wall -Wextra -Werror \
 -ffreestanding -fno-builtin -fno-stack-protector -fomit-frame-pointer \
 -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-pic -fno-pie \
 -nostdlib -static -Wl,-e,_start -Wl,--build-id=none \
 "$root/tools/boottrace/mmap-snapshot.c" -o "$dest/mmap-snapshot"
"${prefix}readelf" -h "$dest/mmap-snapshot"
sha256sum "$dest/mmap-snapshot"
echo 'Built locally only. NOT installed or run on the tablet.'
