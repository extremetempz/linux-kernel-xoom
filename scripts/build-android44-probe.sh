#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build="${XOOM_BUILD_ROOT:?Set the completed android44 kernel build directory}"
dest="${XOOM_ARTIFACT_DIR:?Set its kernel artifact directory}"
version=$(sed -n 's/^CONFIG_LOCALVERSION="\(.*\)"$/\1/p' "$dest/kernel.config")
case "$version" in -wingray-android44|-wingray-android44-touch) ;; *) exit 1;; esac
release="4.4.147$version"
grep -qx 'CONFIG_ANDROID_BINDER_IPC_32BIT=y' "$dest/kernel.config"
test ! -e "$dest/android44-abi-probe"
make -s -C "$build/source" O="$build/out" ARCH=arm \
    INSTALL_HDR_PATH="$build/headers" headers_install
"$build/toolchain/bin/arm-linux-androideabi-gcc" \
    -std=gnu11 -nostdlib -static -marm -march=armv7-a \
    -mfloat-abi=softfp -mfpu=vfpv3-d16 -fomit-frame-pointer \
    -fno-stack-protector -fno-builtin -fno-pic -Wall -Wextra -Werror -O2 \
    -Wl,-e,_start -Wl,--build-id=none -isystem "$build/headers/include" \
    "-DXOOM_ABI_RELEASE=\"$release\"" \
    -I "$build/source/drivers/staging/android" \
    "$root/diagnostic/android44-abi-probe.c" -o "$dest/android44-abi-probe"
python3 - "$dest/android44-abi-probe" "$root/diagnostic/android44-abi-probe.c" "$release" "$dest/kernel.config" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
p=Path(sys.argv[1]);elf=p.read_bytes()
h=subprocess.check_output(['readelf','-lW',str(p)],text=True)
d=subprocess.check_output(['readelf','-dW',str(p)],text=True)
a=subprocess.check_output(['readelf','-A',str(p)],text=True)
assert elf[:7]==b'\x7fELF\x01\x01\x01' and elf[18:20]==b'\x28\x00'
assert 'INTERP' not in h and '(NEEDED)' not in d
assert 'Tag_CPU_arch: v7' in a and 'Tag_Advanced_SIMD_arch:' not in a
assert not subprocess.check_output(['nm','-u',str(p)],text=True).strip()
assert sys.argv[3].encode()+b'\0' in elf
(p.parent/'android44-abi-probe-manifest.json').write_text(json.dumps({
 'sha256':hashlib.sha256(elf).hexdigest(),
 'source_sha256':hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),
 'expected_binder_protocol':7,'physical_execution':False,
 'expected_release':sys.argv[3],
 'kernel_config_sha256':hashlib.sha256(Path(sys.argv[4]).read_bytes()).hexdigest(),
 'purpose':'pre-init Binder, ashmem, sockets and logger gate plus fixed-path read-only open checks and NULL-payload MMC/BLKROSET rejection; no block writes or mounts',
},indent=2)+'\n')
print('Compiled static non-NEON Android4.4 ABI gate; hardware execution pending.')
PY
