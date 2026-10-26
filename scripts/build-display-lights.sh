#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build="${XOOM_BUILD_ROOT:?}"
dest="${XOOM_ARTIFACT_DIR:?}"
"$build/toolchain/bin/arm-linux-androideabi-gcc" -std=gnu11 -nostdlib -shared -fPIC \
 -marm -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -fomit-frame-pointer \
 -fno-stack-protector -fno-builtin -O2 -Wall -Wextra -Werror \
 -Wl,--no-undefined -Wl,-z,relro,-z,now -Wl,-soname,lights.stingray.so \
 -Wl,--build-id=none "$root/android/lights/lights.c" -o "$dest/lights.stingray.so"
python3 - "$root" "$dest" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(sys.argv[1]);p=Path(sys.argv[2]);data=(p/'lights.stingray.so').read_bytes()
assert data[:7]==b'\x7fELF\x01\x01\x01' and data[18:20]==b'\x28\x00'
assert not subprocess.check_output(['nm','-u',str(p/'lights.stingray.so')],text=True).strip()
assert 'Tag_Advanced_SIMD_arch' not in subprocess.check_output(['readelf','-A',str(p/'lights.stingray.so')],text=True)
assert '(NEEDED)' not in subprocess.check_output(['readelf','-d',str(p/'lights.stingray.so')],text=True)
syms=subprocess.check_output(['readelf','-sW',str(p/'lights.stingray.so')],text=True)
assert any('128 OBJECT' in l and l.endswith(' HMI') for l in syms.splitlines())
sha=lambda b:hashlib.sha256(b).hexdigest()
(p/'lights-manifest.json').write_text(json.dumps({'sha256':sha(data),'source_sha256':{n:sha((root/n).read_bytes()) for n in ['android/lights/lights.c','android/lights/kitkat_lights_abi.h']},'purpose':'KitKat ARM32 backlight only, fixed sysfs path, no libc/NEON'},indent=2)+'\n')
print('Verified ARM32 KitKat lights ABI: HMI 128 bytes, no dependencies/NEON.')
PY
