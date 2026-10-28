#!/usr/bin/env bash
# Offline compilation only. Does not pack a boot image or contact a device.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
build="${XOOM_BUILD_ROOT:?Choose a new build directory}"
dest="${XOOM_ARTIFACT_DIR:?Choose a new ignored artifact directory}"
case "$build" in *' '*|*:*) echo 'Build path must have no spaces/colons.' >&2; exit 1;; esac
[ ! -e "$build" ] && [ ! -e "$dest" ] || { echo 'Use new directories.' >&2; exit 1; }
[ -z "$(git -C "$root/sources/kernel-donor" status --porcelain)" ] || { echo 'Commit donor changes first.' >&2; exit 1; }
mkdir -p "$build/source" "$build/toolchain" "$build/out/usr" "$dest"
rsync -a --exclude=.git "$root/sources/kernel-donor/" "$build/source/"
rsync -a "$root/toolchains/android-gcc49/" "$build/toolchain/"
python3 - "$root" "$build/out/usr/wingray-android-runtime.cpio" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1])/'scripts'))
from android44_image import pack_newc
Path(sys.argv[2]).write_bytes(pack_newc({}))
PY
export KBUILD_BUILD_TIMESTAMP='2026-10-28 00:00:00 +0000'
export KBUILD_BUILD_USER=xoom KBUILD_BUILD_HOST=builder KBUILD_BUILD_VERSION=1
args=(-C "$build/source" O="$build/out" ARCH=arm CROSS_COMPILE="$build/toolchain/bin/arm-linux-androideabi-" KCFLAGS='-fno-unwind-tables -fno-asynchronous-unwind-tables')
case "${XOOM_PM_PROFILE:-prepare}" in
 prepare) defconfig=wingray_android44_pmprep_defconfig;;
 wakearm) defconfig=wingray_android44_wakearm_defconfig;;
 *) echo 'Choose prepare or wakearm.' >&2; exit 1;;
esac
make "${args[@]}" "$defconfig"
"$build/source/scripts/config" --file "$build/out/.config" --enable NETDEVICES --enable WLAN --enable MODULES --enable MODULE_UNLOAD --enable CFG80211 --enable WIRELESS_EXT --enable PACKET --disable RD_GZIP --disable RD_BZIP2 --disable RD_LZMA --disable RD_LZO --disable RD_LZ4 --enable RD_XZ --enable WEXT_CORE --enable WEXT_PROC --enable WEXT_PRIV --enable BROADCOM_WIFI --disable BCM4330 --disable BRCMFMAC --disable BRCMFMAC_SDIO
make "${args[@]}" olddefconfig
python3 "$root/tests/test-pm-preparation.py" --config "$build/out/.config"
if [ "${XOOM_PM_PROFILE:-prepare}" = wakearm ]; then
 grep -qx 'CONFIG_MFD_CPCAP_WINGRAY_WAKE_ARM_TEST=y' "$build/out/.config" || { echo 'Apply patch 0160 first.' >&2; exit 1; }
 python3 "$root/tests/test-cpcap-wake-arm.py"
fi
make "${args[@]}" -j"${JOBS:-4}" zImage-dtb modules
cp "$build/out/.config" "$dest/kernel.config"
cp "$build/out/System.map" "$build/out/arch/arm/boot/zImage" "$build/out/arch/arm/boot/zImage-dtb" "$dest/"
cp "$build/out/arch/arm/boot/dts/tegra20-motorola-wingray-android44-wakeirqecc.dtb" "$dest/"
cp "$build/out/drivers/net/wireless/bcmdhd/bcmdhd.ko" "$dest/"
python3 - "$root" "$dest" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
root,out=map(Path,sys.argv[1:])
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
manifest={'purpose':'PM framework compilation only; empty RAM filesystem, not Android', 'boot_image_created':False,'wake_arm_test':'CONFIG_MFD_CPCAP_WINGRAY_WAKE_ARM_TEST=y\n' in (out/'kernel.config').read_text(),'sleep_entry_blocked':True,'soc_suspend_enabled':False,'hardware_wake_validated':False,'hardware_tested':False,'kernel_commit':subprocess.check_output(['git','-C',str(root/'sources/kernel-donor'),'rev-parse','HEAD'],text=True).strip(),'sha256':files}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
PY
echo "PM framework compiled. No boot image; no device operations. Artifacts: $dest"
