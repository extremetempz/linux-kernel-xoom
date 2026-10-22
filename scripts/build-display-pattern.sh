#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build="${XOOM_BUILD_ROOT:?Set XOOM_BUILD_ROOT to the completed display kernel build}"
dest="${XOOM_ARTIFACT_DIR:?Set XOOM_ARTIFACT_DIR to its artifact directory}"
test -f "$dest/kernel.config"
grep -qx 'CONFIG_LOCALVERSION="-wingray-display"' "$dest/kernel.config"
make -s -C "$build/source" O="$build/out" ARCH=arm \
    INSTALL_HDR_PATH="$build/headers" headers_install
test ! -e "$dest/display-pattern"
"$build/toolchain/bin/arm-linux-androideabi-gcc" \
    -nostdlib -static -marm -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 \
    -fomit-frame-pointer -fno-stack-protector -fno-builtin -fno-pic \
    -Wall -Wextra -Werror -O2 -Wl,-e,_start -Wl,--build-id=none \
    -isystem "$build/headers/include" "$root/diagnostic/display-pattern.c" \
    -o "$dest/display-pattern"
readelf -hAlW "$dest/display-pattern" > "$dest/display-pattern-elf.txt"
python3 - "$dest/display-pattern" "$root/diagnostic/display-pattern.c" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
p=Path(sys.argv[1]); data=p.read_bytes()
headers=subprocess.check_output(['readelf','-lW',str(p)],text=True)
dynamic=subprocess.check_output(['readelf','-dW',str(p)],text=True)
attrs=subprocess.check_output(['readelf','-A',str(p)],text=True)
assert data[:7] == b'\x7fELF\x01\x01\x01' and data[18:20] == b'\x28\x00'
assert 'INTERP' not in headers and '(NEEDED)' not in dynamic
assert 'Tag_CPU_arch: v7' in attrs and 'Tag_Advanced_SIMD_arch:' not in attrs
assert not subprocess.check_output(['nm','-u',str(p)],text=True).strip()
(p.parent/'display-pattern-manifest.json').write_text(json.dumps({
    'sha256':hashlib.sha256(data).hexdigest(),
    'source_sha256':hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),
    'purpose':'one-shot color bars, fixed /dev/fb0, reapply the fixed validated mode; no persistent writes',
    'kernel_headers':'built Linux 4.4 source exported ARM UAPI',
},indent=2)+'\n')
print('Verified static ARMv7/VFPv3-D16 display pattern, no NEON or undefined symbols.')
PY
