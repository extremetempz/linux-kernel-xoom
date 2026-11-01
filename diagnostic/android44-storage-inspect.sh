#!/bin/busybox sh
# Read-only userdata/cache inspection. No mkfs, fsck write, mount rw, or service start.
OUT=/run/android44-storage-inspect.txt
: > "$OUT"
say() { echo "$@"; echo "$@" >> "$OUT"; }
say XOOM_STORAGE_INSPECT_BEGIN
say "BOOT_ID $(/bin/busybox cat /proc/sys/kernel/random/boot_id)"
say "UPTIME $(/bin/busybox cat /proc/uptime)"
say "DISK_RO $(/bin/busybox cat /sys/block/mmcblk0/ro)"
for n in 8 9 10; do
 say "PART_RO p$n $(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p$n/ro)"
 say "PART_START p$n $(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p$n/start)"
 say "PART_SIZE p$n $(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p$n/size)"
done
/bin/busybox mkdir -p /mnt/storage-inspect/data /mnt/storage-inspect/cache
inspect_part() {
 number=$1
 dev=/dev/mmcblk0p$number
 name=$2
 size=$(/bin/busybox cat /sys/block/mmcblk0/mmcblk0p$number/size)
 say "INSPECT $name BEGIN"
 # ext4 superblock at byte 1024; dump only metadata bytes, not file contents.
 sb=/run/storage-$name-superblock.bin
 /bin/busybox dd if="$dev" of="$sb" bs=1024 skip=1 count=1 2>/dev/null || { say "SUPERBLOCK_READ_FAILED $name"; say "INSPECT $name END"; return; }
 magic=$(/bin/busybox dd if="$sb" bs=1 skip=56 count=2 2>/dev/null | /bin/busybox od -An -v -tx1 | /bin/busybox tr -d ' \n')
 say "EXT4_MAGIC $name $magic"
 say "SUPERBLOCK_SHA256 $name $(/bin/busybox sha256sum "$sb" | /bin/busybox cut -d' ' -f1)"
 # Parse selected ext4 superblock fields with fixed byte offsets.
 field() { /bin/busybox dd if="$sb" bs=1 skip="$1" count="$2" 2>/dev/null | /bin/busybox od -An -v -tx1 | /bin/busybox tr -d ' \n'; }
 say "EXT4_INODES $name $(field 0 4)"
 say "EXT4_BLOCKS_LO $name $(field 4 4)"
 say "EXT4_FIRST_DATA_BLOCK $name $(field 20 4)"
 say "EXT4_LOG_BLOCK_SIZE $name $(field 24 4)"
 say "EXT4_BLOCKS_PER_GROUP $name $(field 32 4)"
 say "EXT4_FEATURE_COMPAT $name $(field 92 4)"
 say "EXT4_FEATURE_INCOMPAT $name $(field 96 4)"
 say "EXT4_FEATURE_RO_COMPAT $name $(field 100 4)"
 say "EXT4_UUID $name $(field 104 16)"
 say "EXT4_VOLUME_NAME $name $(field 120 16)"
 # Android crypto footer is at the end; dump the final 16 KiB and look for the
 # little-endian cryptfs magic 0xD0B5B1C4. No footer content is printed.
 skip=$((size - 32))
 if [ "$skip" -lt 0 ]; then skip=0; fi
 tail=/run/storage-$name-tail.bin
 /bin/busybox dd if="$dev" of="$tail" bs=512 skip="$skip" count=32 2>/dev/null || say "TAIL_READ_FAILED $name"
 footer=$(/bin/busybox od -An -v -tx1 "$tail" 2>/dev/null | /bin/busybox tr -d ' \n')
 case "$footer" in *c4b1b5d0*) say "ANDROID_CRYPTO_FOOTER $name present_or_candidate";; *) say "ANDROID_CRYPTO_FOOTER $name absent";; esac
 say "TAIL_SHA256 $name $(/bin/busybox sha256sum "$tail" 2>/dev/null | /bin/busybox cut -d' ' -f1)"
 # e2fsck -n opens read-only. It must never repair or replay a journal.
 if [ -x /system/bin/e2fsck ]; then
  LD_LIBRARY_PATH=/system/lib /bin/busybox timeout -s KILL 120 /system/bin/e2fsck -n "$dev" > /run/storage-$name-e2fsck.txt 2>&1
  rc=$?
  say "E2FSCK_N_RC $name $rc"
  /bin/busybox head -c 8192 /run/storage-$name-e2fsck.txt | /bin/busybox sed 's/^/E2FSCK /' >> "$OUT"
 else
  say "E2FSCK_UNAVAILABLE $name"
 fi
 if [ "$magic" = "53ef" ] && [ "$footer" != "${footer#*c4b1b5d0}" ]; then
  say "RO_MOUNT_SKIPPED_ENCRYPTED $name"
 else
  if /bin/busybox mount -t ext4 -o ro,noload,nosuid,nodev "$dev" /mnt/storage-inspect/$name; then
   say "RO_MOUNT_OK $name"
   /bin/busybox ls -la /mnt/storage-inspect/$name 2>&1 | /bin/busybox head -c 8192 | /bin/busybox sed 's/^/LS /' >> "$OUT"
   /bin/busybox umount /mnt/storage-inspect/$name || say "RO_UMOUNT_FAILED $name"
  else
   say "RO_MOUNT_FAILED $name"
  fi
 fi
 say "INSPECT $name END"
}
inspect_part 10 data
inspect_part 9 cache
say "DATA_MOUNT_AFTER_INSPECTION $(/bin/busybox awk '$2=="/data"{print $1" "$3" "$4}' /proc/mounts)"
say "CACHE_MOUNT_AFTER_INSPECTION $(/bin/busybox awk '$2=="/cache"{print $1" "$3" "$4}' /proc/mounts)"
say XOOM_STORAGE_INSPECT_END
