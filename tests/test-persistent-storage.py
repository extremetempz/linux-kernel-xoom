#!/usr/bin/env python3
"""Offline safety gates for the persistent-storage profiles (no device I/O)."""
from pathlib import Path
import re, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
K=ROOT/'sources/kernel-donor'
b=(K/'drivers/mmc/card/block.c').read_text()
boot=(ROOT/'diagnostic/android44-gpu-bootstrap.sh').read_text()
insp=(ROOT/'diagnostic/android44-storage-inspect.sh').read_text()
wt=(ROOT/'diagnostic/android44-storage-write-test.sh').read_text()
img=(ROOT/'scripts/android44_image.py').read_text()
cfg=(K/'arch/arm/configs/wingray_android44_persistent_defconfig').read_text()
geo=re.search(r"XOOM_GEOMETRY'\n(.*?)XOOM_GEOMETRY",boot,re.S).group(1)
parts={int(n):(int(s),int(z)) for n,s,z in (line.split() for line in geo.splitlines())}
checks=[]
def check(name,cond):
    assert cond,name; checks.append(name)
# 1 exact BigPart geometry
check('bigpart geometry',parts[8]==(118784,2097152) and parts[9]==(2215936,1048576) and parts[10]==(3264512,59247616))
# 2 unexpected geometry is rejected by exact shell comparisons
check('geometry rejection',boot.count('partition_start')==1 and boot.count('partition_size')==1 and 'fail partition_start' in boot and 'fail partition_size' in boot)
# 3 existing whole-device read-only profile remains in the driver
check('diagnostic RO preserved','motorola,xoom-firstboot-ro' in b and 'mmc_wingray_firstboot_ro' in b)
# 4 persistent profile selection is DT-gated
check('persistent selection','motorola,xoom-persistent-storage' in b and 'CONFIG_MOTOROLA_WINGRAY_PERSISTENT_STORAGE=y\n' in cfg)
# 5 protected partitions, raw MMC, BLKROSET and BLKPG policy
check('p9/p10 only','partno != 9 && partno != 10' in b)
check('raw MMC rejected','cmd == MMC_IOC_CMD || cmd == MMC_IOC_MULTI_CMD' in b)
check('BLKPG rejected','cmd == BLKPG || cmd == BLKRRPART' in b and 'get_disk_ro(disk)' in (ROOT/'sources/kernel-donor/block/ioctl.c').read_text())
check('NULL BLKROSET','if (!arg)' in b and 'return -EROFS' in b)
# 6/7 data/cache mount selection and independent mount failures
check('data p10', '/dev/mmcblk0p10 /data' in boot)
check('cache p9', '/dev/mmcblk0p9 /cache' in boot)
check('mount failures fatal','fail persistent_data_mount' in boot and 'fail persistent_cache_mount' in boot)
# 8 no tmpfs fallback in persistent branch
check('persistent no tmpfs',boot.index('if [ "$persistent" = 1 ]') < boot.index('tmpfs -o size=256m') and 'persistent_data_mount' in boot)
# 9 no duplicate Android mounts: generated init does not call mount_all
check('single mount path','mount_all' not in (ROOT/'diagnostic/android44-gpu-report.sh').read_text())
gen=(ROOT/'scripts/android44_image.py').read_text()
check('init no mount_all','mount_all' not in gen)
# 10 no recursive ownership changes
check('no recursive chown','chown -R' not in boot and 'chmod -R' not in boot)
# 11 existing userdata preservation / no format/repartition/wipe
check('no format','mkfs' not in boot and 'mke2fs' not in boot and 'wipefs' not in boot)
check('no repartition','sgdisk' not in boot and 'parted' not in boot and 'BLKPG' not in boot)
check('no wipe','rm -rf /data' not in boot and 'rm -rf /cache' not in boot)
# 12/13 missing/corrupt filesystem fail closed; no tmpfs fallback
check('ext4 magic gate','data_not_ext4' in boot and 'cache_not_ext4' in boot)
check('no rw mount fallback','mount -t ext4 -o rw' in boot and '|| fail' in boot[boot.index('persistent_data_mount')-160:boot.index('persistent_data_mount')+40])
# 14 encryption footer gate
check('encryption gate','c4b1b5d0' in boot and 'encrypted_userdata' in boot and 'encrypted_cache' in boot)
# 15/16/17 destructive guards in all new scripts
for name,text in (('inspect',insp),('write-test',wt)):
    check(name+' no mkfs', 'mkfs.' not in text and 'mke2fs' not in text)
    check(name+' no wipe', 'rm -rf' not in text)
    check(name+' fixed paths', ('inspect_part 10 data' in text and 'inspect_part 9 cache' in text) if name=='inspect' else ('/data/local/xoom-storage-test' in text and 'mmcblk0p10/ro' in text))
# 18 GPU/Wi-Fi integration remains in the shared bootstrap
check('GPU overlays','xoom-hw' in boot and 'xoom-egl' in boot and 'gralloc.tegra' in boot)
check('Wi-Fi preserved','xoom-wifi-load' in (ROOT/'scripts/prepare-android-gpu.py').read_text())
# 19 LP2/suspend retained
for sym in ('MOTOROLA_WINGRAY_LP2_TEST','MOTOROLA_WINGRAY_DEVICEPM_TEST','MOTOROLA_WINGRAY_PM_PREPARE'):
    check('retain '+sym,'CONFIG_'+sym+'=y\n' in cfg)
# 20 fstab persistent and no noload on rw data/cache
fstab=img[img.index("if persistent:"):img.index("else:",img.index("if persistent:"))]
check('persistent fstab','/data ext4 rw' in fstab and '/cache ext4 rw' in fstab)
check('no noload rw', 'noload' not in fstab[fstab.index('/data'):])
# Write test is fixed and verification-only on second boot
check('write test fixed', 'EXPECT=4f5a76d96d52a7902acb25f86971d101fc9fae1d7d97039fb6f0fbbb0a7e13ee' in wt and 'set -C' in wt)
check('write test no auto reboot','reboot' not in wt and '/system/bin/reboot' not in boot)
print(f'PASS {len(checks)} persistent-storage offline gates; no device/filesystem writes')
