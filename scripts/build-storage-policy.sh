#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build="${XOOM_BUILD_ROOT:?Completed kernel build directory required}"
dest="${XOOM_ARTIFACT_DIR:?New runtime directory required}"
test ! -e "$dest/storage-policy"
"$build/toolchain/bin/arm-linux-androideabi-gcc" -std=gnu11 -nostdlib -static \
 -marm -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -fomit-frame-pointer \
 -fno-stack-protector -fno-builtin -fno-pic -Wall -Wextra -Werror -O2 \
 -Wl,-e,_start -Wl,--build-id=none \
 "$root/diagnostic/storage-policy.c" -o "$dest/storage-policy"
python3 - "$dest/storage-policy" "$root/diagnostic/storage-policy.c" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]);data=p.read_bytes()
h=subprocess.check_output(['readelf','-lW',str(p)],text=True)
d=subprocess.check_output(['readelf','-dW',str(p)],text=True)
a=subprocess.check_output(['readelf','-A',str(p)],text=True)
assert data[:7]==b'\x7fELF\x01\x01\x01' and data[18:20]==b'\x28\0'
assert 'INTERP' not in h and '(NEEDED)' not in d and 'Tag_Advanced_SIMD_arch:' not in a
assert not subprocess.check_output(['nm','-u',str(p)],text=True).strip()
(p.parent/'storage-policy-manifest.json').write_text(json.dumps({
 'sha256':hashlib.sha256(data).hexdigest(),
 'source_sha256':hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),
 'paths':['/dev/mmcblk0p9','/dev/mmcblk0p10'],
 'operations':['BLKROSET 0','BLKROGET'],
 'refuses_inspection':True,'writes_media':False},indent=2)+'\n')
print('Built fixed p9/p10 policy helper; physical execution pending.')
PY
