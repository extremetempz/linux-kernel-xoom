#!/bin/busybox sh
# One-shot bounded child; USB reporting remains independent. RAM files only.
i=0
while [ ! -c /dev/nvmap ] && [ "$i" -lt 20 ]; do
 /bin/busybox sleep 1
 i=$((i+1))
done
echo XOOM_NVMAP_TEST_BEGIN
/bin/busybox timeout -s KILL 30 /bin/nvmap-allocator-probe
rc=$?
echo "XOOM_NVMAP_TEST_EXIT $rc"
echo XOOM_NVMAP_TEST_END
