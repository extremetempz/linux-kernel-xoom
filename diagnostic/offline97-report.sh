#!/bin/busybox sh
/bin/busybox sh /bin/base-report "$1" || exit 1
echo XOOM_OFFLINE97_BEGIN
echo 'scope=validation_only android=absent twrp=absent mass_storage=absent physical_repair=disabled'
echo 'pid1=offline97-init mounts=virtual_only writable_fixtures=ram_only'
/bin/busybox cat /run/offline97-state /run/offline97-ramtest.txt
/bin/busybox sha256sum /bin/e2fsck
echo XOOM_OFFLINE97_END
