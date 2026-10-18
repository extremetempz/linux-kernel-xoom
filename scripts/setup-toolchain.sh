#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
dest="$root/toolchains/android-gcc49"
archive="$root/toolchains/android-gcc49.tar.gz"
mkdir -p "$root/toolchains"
curl --fail --location --retry 2 \
  'https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/arm/arm-linux-androideabi-4.9/+archive/refs/tags/android-8.1.0_r1.tar.gz' \
  -o "$archive"
printf '%s  %s\n' b84606f4cf9b8f13fe7a874deac5d2f02e0eb5af24ee56530e13d5c3226e56de "$archive" | sha256sum --check
mkdir -p "$dest"
tar -xzf "$archive" -C "$dest"
# The official wrapper is Python 3 compatible but uses /usr/bin/python.
python3 - "$dest/bin/arm-linux-androideabi-gcc" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
p.write_text(p.read_text().replace('#!/usr/bin/python\n', '#!/usr/bin/python3\n', 1))
PY
"$dest/bin/arm-linux-androideabi-gcc" --version
