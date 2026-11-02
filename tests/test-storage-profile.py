#!/usr/bin/env python3
"""Source gates for persistent storage; no device or filesystem writes."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
K=ROOT/'sources/kernel-donor'
dts=(K/'arch/arm/boot/dts/tegra20-motorola-wingray-android44-persistent.dts').read_text()
inspect=(K/'arch/arm/boot/dts/tegra20-motorola-wingray-android44-persistent-inspect.dts').read_text()
cfg=(K/'arch/arm/configs/wingray_android44_persistent_defconfig').read_text()
block=(K/'drivers/mmc/card/block.c').read_text()
boot=(ROOT/'diagnostic/android44-gpu-bootstrap.sh').read_text()
img=(ROOT/'scripts/android44_image.py').read_text()
assert 'motorola,xoom-persistent-storage' in dts
assert '/delete-property/ motorola,xoom-firstboot-ro' in dts
assert 'motorola,wingray-storage-inspect' in inspect
assert 'CONFIG_MOTOROLA_WINGRAY_PERSISTENT_STORAGE=y\n' in cfg
assert 'CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="tegra20-motorola-wingray-android44-persistent"' in cfg
assert 'mmc_wingray_persistent_storage' in block
assert 'partno != 9 && partno != 10' in block
assert 'cmd == BLKPG || cmd == BLKRRPART' in block
# Existing whole-device firstboot policy must remain in the driver.
assert 'motorola,xoom-firstboot-ro' in block
# Persistent bootstrap must never substitute tmpfs for /data or /cache.
assert 'persistent_data_mount' in boot and 'persistent_cache_mount' in boot
assert 'tmpfs /data' in boot and 'tmpfs /cache' in boot  # only RAM branch
assert boot.index('if [ "$persistent" = 1 ]') < boot.index('tmpfs -o size=256m')
assert 'mkfs' not in boot and 'fsck' not in boot and 'wipefs' not in boot
assert 'android44-storage-inspect' in boot and 'storage-policy' in boot
# fstab is generated only for the persistent config; data/cache are rw.
assert "b'/dev/block/mmcblk0p10 /data ext4 rw,noatime" in img
assert 'nomblk_io_submit,errors=panic' in img
assert 'noload' not in img[img.index("b'/dev/block/mmcblk0p10"):img.index("b'/dev/block/mmcblk0p10")+160]
print('PASS persistent profile, partition policy, bootstrap and fstab source gates')
