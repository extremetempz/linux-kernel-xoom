#!/usr/bin/env python3
"""Fault-test the actual donor channel registration function without devices."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'sources/kernel-donor/drivers/staging/tegra/video/host/bus_client.c').read_text()
start = re.search(r'^int nvhost_client_user_init\(', source, re.M).start()
end = source.index('\nint nvhost_client_device_init(', start)
function = source[start:end]
fixture = r'''
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/types.h>
#define THIS_MODULE ((void *)1)
#define IFACE_NAME "nvhost"
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define dev_err(...) ((void)0)
struct cdev { dev_t dev; void *owner; };
struct nvhost_channel { struct cdev cdev; void *node; };
struct nvhost_device { struct nvhost_channel *channel; int index; const char *name; };
struct nvhost_master { void *nvhost_class; };
static int ops, region, chars, node, fail, stage;
#define nvhost_channelops ops
static struct nvhost_master host;
static int step(void) { return ++stage == fail; }
static struct nvhost_master *nvhost_get_host(struct nvhost_device *d) { (void)d; return &host; }
static int alloc_chrdev_region(dev_t *d, int base, int n, const char *name) {
 (void)base; (void)n; (void)name; assert(!region && !chars && !node);
 if (step()) return -EBUSY;
 *d = 5; region = 1; return 0;
}
static void cdev_init(struct cdev *c, void *p) { assert(p == &ops); c->dev = 0; }
static int cdev_add(struct cdev *c, dev_t d, int n) {
 (void)n; assert(region && !chars && d == 5);
 if (step()) return -EINVAL;
 chars = 1; c->dev = d; return 0;
}
static void *device_create(void *cls, void *parent, dev_t d, void *data, const char *fmt, const char *name) {
 (void)cls; (void)parent; (void)data; (void)fmt; (void)name;
 assert(chars && d == 5);
 if (step()) return (void *)(intptr_t)-ENOMEM;
 node = 1; return &node;
}
static void cdev_del(struct cdev *c) { assert(chars && !node && c->dev == 5); chars = 0; }
static void unregister_chrdev_region(dev_t d, int n) { (void)n; assert(region && !chars && !node && d == 5); region = 0; }
'''
main = r'''
int main(void) {
 struct nvhost_channel ch = {0};
 struct nvhost_device dev = { &ch, 1, "gr3d" };
 const int errors[] = {0, -EBUSY, -EINVAL, -ENOMEM};
 for (int retry = 0; retry < 3; retry++) {
  for (fail = 1; fail <= 3; fail++) {
   stage = 0;
   assert(nvhost_client_user_init(&dev) == errors[fail]);
   assert(!region && !chars && !node && !ch.node);
  }
 }
 fail = stage = 0;
 assert(!nvhost_client_user_init(&dev));
 assert(region && chars && node && ch.node == &node);
 /* Fixture teardown of successful publication, not a driver remove test. */
 node = 0; ch.node = NULL; cdev_del(&ch.cdev); unregister_chrdev_region(5, 1);
 puts("PASS actual channel publication: three failure stages, retries, success (UBSan)");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / 'test.c'
    path.write_text(fixture + function + main)
    subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', '-fsanitize=undefined', str(path), '-o', tmp + '/test'], check=True)
    subprocess.run([tmp + '/test'], check=True)
