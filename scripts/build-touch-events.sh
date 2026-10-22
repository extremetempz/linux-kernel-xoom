#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build="${XOOM_BUILD_ROOT:?Set the completed touch kernel build directory}"
dest="${XOOM_ARTIFACT_DIR:?Set its kernel artifact directory}"
grep -qx 'CONFIG_LOCALVERSION="-wingray-android44-touch"' "$dest/kernel.config"
grep -qx 'CONFIG_TOUCHSCREEN_ATMEL_MXT=y' "$dest/kernel.config"
grep -qx 'CONFIG_INPUT_EVDEV=y' "$dest/kernel.config"
test ! -e "$dest/touch-events"
test ! -e "$dest/touch-events-manifest.json"
make -s -C "$build/source" O="$build/out" ARCH=arm \
    INSTALL_HDR_PATH="$build/headers" headers_install
# Exported Linux 4.4 input.h names libc sys/* headers. Delegate those three
# names to the exported Linux ARM types/ioctl/time UAPI, without adding libc.
touch_uapi_shim=$(mktemp -d /tmp/xoom-touch-uapi-XXXXXX)
trap 'rm -rf -- "$touch_uapi_shim"' EXIT
mkdir "$touch_uapi_shim/sys"
printf '#include <linux/time.h>\n' > "$touch_uapi_shim/sys/time.h"
printf '#include <asm/ioctl.h>\n' > "$touch_uapi_shim/sys/ioctl.h"
printf '#include <linux/types.h>\n' > "$touch_uapi_shim/sys/types.h"
"$build/toolchain/bin/arm-linux-androideabi-gcc" \
    -std=gnu11 -nostdlib -static -marm -march=armv7-a \
    -mfloat-abi=softfp -mfpu=vfpv3-d16 -fomit-frame-pointer \
    -fno-stack-protector -fno-builtin -fno-pic -Wall -Wextra -Werror -O2 \
    -Wl,-e,_start -Wl,--build-id=none -isystem "$touch_uapi_shim" \
    -isystem "$build/headers/include" \
    "$root/diagnostic/touch-events.c" -o "$dest/touch-events"
readelf -hAlW "$dest/touch-events" > "$dest/touch-events-elf.txt"
python3 - "$dest/touch-events" "$root/diagnostic/touch-events.c" "$dest/kernel.config" <<'PY'
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
(p.parent/'touch-events-manifest.json').write_text(json.dumps({
 'sha256':hashlib.sha256(elf).hexdigest(),
 'source_sha256':hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),
 'kernel_config_sha256':hashlib.sha256(Path(sys.argv[3]).read_bytes()).hexdigest(),
 'expected_release':'4.4.147-wingray-android44-touch',
 'expected_board':'motorola,wingray',
 'expected_input_name':'Atmel maXTouch Touchscreen',
 'deadline_seconds':5,'max_input_events':8192,'max_contact_records':64,
 'physical_execution':False,
 'purpose':'fixed read-only independent evdev sample; no grab, injection, raw bus access or persistent writes',
},indent=2)+'\n')
print('Compiled static non-NEON five-second touch observer; hardware execution pending.')
PY
