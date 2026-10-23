#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build="${XOOM_BUILD_ROOT:?Completed kernel build directory required}"
dest="${XOOM_ARTIFACT_DIR:?New runtime directory required}"
version=$(sed -n 's/^CONFIG_LOCALVERSION="\(.*\)"$/\1/p' "$dest/kernel.config")
case "$version" in
 -wingray-android44-l2|-wingray-android44-smp) count=1;;
 -wingray-android44-smp2|-wingray-android44-smptrace) count=2;;
 *) exit 1;;
esac
release="4.4.147$version"
test ! -e "$dest/cpu-handoff-probe"
"$build/toolchain/bin/arm-linux-androideabi-gcc" -std=gnu11 -nostdlib -static \
 -marm -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -fomit-frame-pointer \
 -fno-stack-protector -fno-builtin -fno-pic -Wall -Wextra -Werror -O2 \
 -Wl,-e,_start -Wl,--build-id=none "-DXOOM_CPU_RELEASE=\"$release\"" \
 "-DXOOM_CPU_COUNT=$count" "$root/diagnostic/cpu-handoff-probe.c" -o "$dest/cpu-handoff-probe"
python3 - "$dest/cpu-handoff-probe" "$root/diagnostic/cpu-handoff-probe.c" "$dest/kernel.config" "$release" "$count" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]);data=p.read_bytes()
h=subprocess.check_output(['readelf','-lW',str(p)],text=True)
d=subprocess.check_output(['readelf','-dW',str(p)],text=True)
a=subprocess.check_output(['readelf','-A',str(p)],text=True)
assert data[:7]==b'\x7fELF\x01\x01\x01' and data[18:20]==b'\x28\0'
assert 'INTERP' not in h and '(NEEDED)' not in d and 'Tag_Advanced_SIMD_arch:' not in a
assert not subprocess.check_output(['nm','-u',str(p)],text=True).strip()
assert sys.argv[4].encode()+b'\0' in data
(p.parent/'cpu-handoff-probe-manifest.json').write_text(json.dumps({
 'sha256':hashlib.sha256(data).hexdigest(),'source_sha256':hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),
 'kernel_config_sha256':hashlib.sha256(Path(sys.argv[3]).read_bytes()).hexdigest(),
 'expected_release':sys.argv[4],'expected_cpu_count':int(sys.argv[5]),'private_bytes':16384,'iterations':64,
 'purpose':'own-process CPU affinity and bounded private-memory migration check; no hardware control or persistent writes',
 'physical_execution':False},indent=2)+'\n')
print('Built bounded static ARM CPU migration probe; hardware execution pending.')
PY
