#!/usr/bin/env python3
"""Exercise actual block-core BLKROSET dispatch through the actual MMC policy.

All devices and user pointers are host scalar mocks. This demonstrates the
generic fallback which the protected profile must stop, without device I/O.
"""
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
mmc = (ROOT / 'sources/kernel-donor/drivers/mmc/card/block.c').read_text()
block = (ROOT / 'sources/kernel-donor/block/ioctl.c').read_text()


def extract(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    position, depth = opening + 1, 1
    while depth:
        depth += (source[position] == '{') - (source[position] == '}')
        position += 1
    return source[start:position] + '\n'


actual = (extract(mmc, 'static bool mmc_wingray_firstboot_ro(') +
          extract(mmc, 'static int mmc_blk_ioctl(struct block_device') +
          extract(block, 'int __blkdev_driver_ioctl(') +
          extract(block, 'static inline int is_unrecognized_ioctl(') +
          extract(block, 'static int blkdev_roset('))

fixture = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <linux/fs.h>
#define __user
#define MMC_CAP_NONREMOVABLE 1
#define MMC_IOC_CMD 101
#define MMC_IOC_MULTI_CMD 102
#define CAP_SYS_ADMIN 21
#define ENOIOCTLCMD 515
typedef unsigned fmode_t;
struct device_node { bool bigpart, firstboot; };
struct device { struct device_node *of_node; };
struct mmc_host { unsigned caps; struct device *parent; };
struct mmc_card { struct mmc_host *host; bool mmc; };
struct mmc_blk_data { struct { struct mmc_card *card; } queue; };
struct block_device;
struct block_device_operations {
    int (*ioctl)(struct block_device *, fmode_t, unsigned, unsigned long);
};
struct gendisk { struct mmc_blk_data *private_data; const struct block_device_operations *fops; };
struct block_device { struct gendisk *bd_disk; int policy; };
struct mmc_ioc_cmd {};
struct mmc_ioc_multi_cmd {};
static bool wingray, admin;
static unsigned get_calls, set_calls, capability_calls, raw_calls;
static bool of_machine_is_compatible(const char *name)
{
    assert(!strcmp(name, "motorola,wingray"));
    return wingray;
}
static bool mmc_card_mmc(struct mmc_card *card) { return card->mmc; }
static bool of_property_read_bool(struct device_node *node, const char *name)
{
    if (!node) return false;
    if (!strcmp(name, "motorola,xoom-bigpart")) return node->bigpart;
    assert(!strcmp(name, "motorola,xoom-firstboot-ro"));
    return node->firstboot;
}
static bool capable(int capability)
{
    assert(capability == CAP_SYS_ADMIN);
    ++capability_calls;
    return admin;
}
static int read_user(int *value, const int *pointer)
{
    ++get_calls;
    if (!pointer) return -EFAULT;
    *value = *pointer;
    return 0;
}
#define get_user(value, pointer) read_user(&(value), (pointer))
static void set_device_ro(struct block_device *bdev, int value)
{
    ++set_calls;
    bdev->policy = value;
}
static int mmc_blk_ioctl_cmd(struct block_device *bdev, struct mmc_ioc_cmd *p)
{
    (void)bdev; (void)p; ++raw_calls; return 11;
}
static int mmc_blk_ioctl_multi_cmd(struct block_device *bdev, struct mmc_ioc_multi_cmd *p)
{
    (void)bdev; (void)p; ++raw_calls; return 12;
}
'''

main = r'''
static void reset(void)
{
    get_calls = set_calls = capability_calls = raw_calls = 0;
}
int main(void)
{
    struct device_node node;
    struct device device = { &node };
    struct mmc_host host = { 1, &device };
    struct mmc_card card = { &host, true };
    struct mmc_blk_data md = { { &card } };
    const struct block_device_operations ops = { mmc_blk_ioctl };
    struct gendisk disk = { &md, &ops };
    struct block_device bdev = { &disk, 1 };
    unsigned cases = 0;
    for (unsigned bits = 0; bits < 64; ++bits) {
        wingray = !!(bits & 1);
        card.mmc = !!(bits & 2);
        host.caps = !!(bits & 4);
        host.parent = (bits & 8) ? &device : NULL;
        node.bigpart = !!(bits & 16);
        node.firstboot = !!(bits & 32);
        bool protected = bits == 63;
        for (unsigned permission = 0; permission < 2; ++permission) {
            admin = permission;
            /* NULL and scalar pointers exist only inside this host fixture. */
            for (int requested = -1; requested <= 1; ++requested) {
                int *payload = requested < 0 ? NULL : &requested;
                reset(); bdev.policy = 1;
                int result = blkdev_roset(&bdev, 0, BLKROSET, (unsigned long)payload);
                ++cases;
                if (protected) {
                    assert(result == -EROFS && bdev.policy == 1);
                    assert(!capability_calls && !get_calls && !set_calls);
                } else if (!admin) {
                    assert(result == -EACCES && capability_calls == 1);
                    assert(!get_calls && !set_calls && bdev.policy == 1);
                } else if (!payload) {
                    assert(result == -EFAULT && get_calls == 1);
                    assert(!set_calls && bdev.policy == 1);
                } else {
                    /* Shows original core fallback can clear or set the flag. */
                    assert(result == 0 && get_calls == 1 && set_calls == 1);
                    assert(bdev.policy == requested);
                }
                assert(raw_calls == 0);
            }
        }
    }
    /* Missing DT and non-MMC disk metadata preserve generic behavior too. */
    wingray = card.mmc = node.bigpart = node.firstboot = admin = true;
    host.caps = 1; host.parent = &device; device.of_node = NULL;
    int zero = 0;
    reset(); bdev.policy = 1;
    assert(blkdev_roset(&bdev, 0, BLKROSET, (unsigned long)&zero) == 0);
    assert(get_calls == 1 && set_calls == 1 && bdev.policy == 0);
    device.of_node = &node; disk.private_data = NULL;
    reset(); bdev.policy = 1;
    assert(blkdev_roset(&bdev, 0, BLKROSET, (unsigned long)&zero) == 0);
    assert(get_calls == 1 && set_calls == 1 && bdev.policy == 0);
    /* An unrecognized ioctl still receives generic fallback without an ioctl method. */
    const struct block_device_operations no_ops = { NULL };
    disk.fops = &no_ops;
    reset(); bdev.policy = 1;
    assert(blkdev_roset(&bdev, 0, BLKROSET, (unsigned long)&zero) == 0);
    assert(get_calls == 1 && set_calls == 1 && bdev.policy == 0);
    printf("PASS actual generic BLKROSET/MMC dispatch: %u scope/privilege/payload cases; protected profile stops before get_user/set_device_ro; outside scope preserves generic flag changes.\n", cases);
}
'''

with tempfile.TemporaryDirectory(prefix='xoom-blkroset-') as directory:
    path = Path(directory)
    (path / 'test.c').write_text(fixture + actual + main)
    subprocess.run([
        'cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
        '-Wno-unused-parameter', '-O2', '-fsanitize=undefined',
        str(path / 'test.c'), '-o', str(path / 'test'),
    ], check=True)
    subprocess.run([str(path / 'test')], check=True)
