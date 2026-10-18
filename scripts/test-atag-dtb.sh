#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/sources/kernel-donor"
work="$(mktemp -d /tmp/xoom-atag-test.XXXXXX)"
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/asm"
# Use the donor's actual ARM UAPI layout; only host compilation type aliases
# are supplied here. No copy of the conversion algorithm exists in the test.
printf '#include "%s/arch/arm/include/uapi/asm/setup.h"\n' "$src" > "$work/asm/setup.h"
cc -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer \
 -Wno-pointer-to-int-cast -D__deprecated= -Du32=uint32_t -Du64=uint64_t \
 -DCONFIG_ARM_ATAG_DTB_COMPAT_CMDLINE_EXTEND \
 -I"$work" -I"$src/scripts/dtc/libfdt" \
 "$root/tests/test-atag-dtb.c" "$src/arch/arm/boot/compressed/atags_to_fdt.c" \
 "$src/scripts/dtc/libfdt/fdt.c" "$src/scripts/dtc/libfdt/fdt_ro.c" \
 "$src/scripts/dtc/libfdt/fdt_rw.c" "$src/scripts/dtc/libfdt/fdt_wip.c" \
 "$src/scripts/dtc/libfdt/fdt_strerror.c" -o "$work/test"
ASAN_OPTIONS=detect_leaks=0 "$work/test" "${1:-$root/artifacts/wingray44/tegra20-motorola-wingray.dtb}"
