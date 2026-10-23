#!/usr/bin/env bash
# Offline compile gate only: never packages a boot image or touches a device.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build="${XOOM_GRAPHICS_BUILD_ROOT:-$(mktemp -d /tmp/xoom-decatf-graphics.XXXXXX)}"
dest="${XOOM_GRAPHICS_ARTIFACT_DIR:?Set a NEW ignored artifact directory}"
legacy_fb="${XOOM_GRAPHICS_LEGACY_FB:-0}"
case "$legacy_fb" in 0|1) ;; *) echo 'XOOM_GRAPHICS_LEGACY_FB must be 0 or 1.' >&2; exit 1;; esac
case "$build" in *' '*|*:* ) echo 'Build path cannot contain spaces/colons.' >&2; exit 1;; esac
[ ! -e "$dest" ] || { echo 'Refuse to overwrite evidence.' >&2; exit 1; }
[ ! -d "$build" ] || [ -z "$(find "$build" -mindepth 1 -maxdepth 1 -print -quit)" ] || {
 echo 'Require a new or empty build directory; refuse stale sources.' >&2; exit 1;
}
[ -z "$(git -C "$root/sources/kernel-donor" status --porcelain)" ] || {
 echo 'Commit kernel changes before measuring a build.' >&2; exit 1;
}
source_revision="$(git -C "$root/sources/kernel-donor" rev-parse HEAD)"
mkdir -p "$build/source" "$build/toolchain" "$build/out" "$dest"
rsync -a --exclude=.git "$root/sources/kernel-donor/" "$build/source/"
rsync -a "$root/toolchains/android-gcc49/" "$build/toolchain/"
args=(-C "$build/source" O="$build/out" ARCH=arm CROSS_COMPILE="$build/toolchain/bin/arm-linux-androideabi-" KCFLAGS='-fno-unwind-tables -fno-asynchronous-unwind-tables')
make "${args[@]}" wingray_android44_smp2_defconfig
cfg="$build/source/scripts/config"
"$cfg" --file "$build/out/.config" -d DRM -d TEGRA_HOST1X -e MEMORY -d TEGRA20_MC \
 -e STAGING -e TEGRA_DOWNSTREAM -e TEGRA_GRHOST -e TEGRA_NVMAP -e TEGRA_DC \
 -e FB -e FB_TEGRA -d TEGRA_DC_EXTENSIONS -d TEGRA_OVERLAY -d FB_TEGRA_CMC623 \
 -d FRAMEBUFFER_CONSOLE -d FB_TEGRA_WINGRAY_LEGACY
if [ "$legacy_fb" = 1 ]; then
 "$cfg" --file "$build/out/.config" -e FB_TEGRA_WINGRAY_LEGACY
fi
make "${args[@]}" olddefconfig
cp "$build/out/.config" "$dest/kernel.config"
# Resolve the REAL Kconfig menu, not text substitutions or a model of its logic.
"$cfg" --file "$build/out/.config" -e MEMORY -e TEGRA20_MC -e TEGRA_DOWNSTREAM
make "${args[@]}" olddefconfig
python3 - "$build/out/.config" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text().splitlines()
assert 'CONFIG_FB_TEGRA_WINGRAY_LEGACY=y' not in s
assert 'CONFIG_MEMORY=y' in s and 'CONFIG_TEGRA20_MC=y' in s
assert 'CONFIG_TEGRA_DOWNSTREAM=y' not in s, 'Two MC owners accepted'
print('PASS actual Kconfig: modern MC excludes legacy downstream stack')
PY
cp "$build/out/.config" "$dest/modern-mc-negative.config"
if [ "$legacy_fb" = 1 ]; then
 for conflict in TEGRA_DC_EXTENSIONS TEGRA_OVERLAY FRAMEBUFFER_CONSOLE; do
  cp "$dest/kernel.config" "$build/out/.config"
  "$cfg" --file "$build/out/.config" -d TEGRA_DC_EXTENSIONS -d TEGRA_OVERLAY -d FRAMEBUFFER_CONSOLE
  if [ "$conflict" = FRAMEBUFFER_CONSOLE ]; then
   "$cfg" --file "$build/out/.config" -e VT -e VT_CONSOLE
  fi
  "$cfg" --file "$build/out/.config" -e "$conflict" -e FB_TEGRA_WINGRAY_LEGACY
  make "${args[@]}" olddefconfig
  python3 - "$build/out/.config" "$conflict" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text().splitlines()
assert 'CONFIG_'+sys.argv[2]+'=y' in s
assert 'CONFIG_FB_TEGRA_WINGRAY_LEGACY=y' not in s
print('PASS actual Kconfig: incompatible display owner excludes Wingray ABI:',sys.argv[2])
PY
  cp "$build/out/.config" "$dest/negative-$conflict.config"
 done
fi
cp "$dest/kernel.config" "$build/out/.config"
make "${args[@]}" olddefconfig
python3 - "$build/out/.config" "$legacy_fb" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text().splitlines()
assert ('CONFIG_FB_TEGRA_WINGRAY_LEGACY=y' in s)==(sys.argv[2]=='1')
for option in ['TEGRA_DOWNSTREAM','TEGRA_GRHOST','TEGRA_NVMAP','TEGRA_DC','FB_TEGRA','SMP','CACHE_L2X0']:
 assert f'CONFIG_{option}=y' in s,option
for option in ['DRM','TEGRA_HOST1X','TEGRA20_MC','MACH_SAMSUNG_VARIATION_TEGRA','MACH_SAMSUNG_P4WIFI','FB_TEGRA_CMC623','CPU_FREQ','SUSPEND']:
 assert f'CONFIG_{option}=y' not in s and f'CONFIG_{option}=m' not in s,option
PY
make "${args[@]}" -j"${JOBS:-4}" vmlinux
cp "$build/out/vmlinux" "$build/out/System.map" "$dest/"
python3 - "$dest" "$source_revision" "$legacy_fb" <<'PY'
from pathlib import Path
import hashlib,json,os,sys
p=Path(sys.argv[1]);names={x.split()[-1] for x in (p/'System.map').read_text().splitlines() if len(x.split())==3}
for name in ['nvhost_probe','nvmap_probe','tegra_dc_probe','tegra_fb_register']:assert name in names,name
for name in ['cmc623_resume','cmc623_suspend','tegra_drm_probe']:assert name not in names,name
legacy_symbols=any(n.startswith('tegra_fb_legacy_ioctl') for n in names)
assert legacy_symbols==(sys.argv[3]=='1'), 'Legacy framebuffer selection/link disagreement'
files=['vmlinux','System.map','kernel.config','modern-mc-negative.config']+[f.name for f in sorted(p.glob('negative-*.config'))]
manifest={'source_revision':sys.argv[2],'legacy_rgb_framebuffer_enabled':sys.argv[3]=='1','compile_only':True,'hardware_tested':False,'flashable_image':False,'accelerated_graphics_working':False,'files':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in files},'limits':['No GPU DT/resource profile or userspace overlay packaged.','Optional framebuffer path supports synchronous, unscaled, linear RGB only; no device test.','No engine submission, fence, memory ownership or clock/voltage validation.']}
with (p/'manifest.json').open('x') as f:
 f.write(json.dumps(manifest,indent=2)+'\n');f.flush();os.fsync(f.fileno())
for name in manifest['files']:
 with (p/name).open('rb') as f:os.fsync(f.fileno())
PY
echo "Decatf legacy graphics full ARM link passed. Compile evidence: $dest"
echo 'NOT a deployable graphics kernel; no board resources activated or boot image made.'
