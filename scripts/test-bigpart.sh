#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
scratch="$(mktemp -d /tmp/xoom-bigpart-tests.XXXXXX)"
mkdir -p "$scratch/linux"
# These headers supply only kernel plumbing in the C file; the host test
# supplies that plumbing explicitly and compiles the real remapping logic.
touch "$scratch/linux/device.h" "$scratch/linux/of.h" "$scratch/linux/string.h"
cc -std=c11 -Wall -Wextra -Wno-sign-compare -Werror \
  -fsanitize=undefined,address -g \
  -I "$scratch" -I "$root/sources/kernel-donor/block/partitions" \
  "$root/tests/test-bigpart.c" -o "$scratch/test-bigpart"
ASAN_OPTIONS="detect_leaks=0${ASAN_OPTIONS:+:$ASAN_OPTIONS}" "$scratch/test-bigpart"
