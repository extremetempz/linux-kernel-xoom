#!/usr/bin/env python3
"""Compile actual MMC first-boot scope and raw-ioctl dispatch; no device I/O."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'sources/kernel-donor/drivers/mmc/card/block.c').read_text()
def extract(signature):
 start=source.index(signature);op=source.index('{',start);pos=op+1;depth=1
 while depth:depth+=(source[pos]=='{')-(source[pos]=='}');pos+=1
 return source[start:pos]+'\n'
actual=extract('static bool mmc_wingray_firstboot_ro(')+extract('static int mmc_blk_ioctl(struct block_device')
fixture=r'''
#include <assert.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
#define MMC_CAP_NONREMOVABLE 1
#define MMC_IOC_CMD 101
#define MMC_IOC_MULTI_CMD 102
#define __user
typedef unsigned fmode_t;
struct device_node { bool bigpart,firstboot; };
struct device { struct device_node *of_node; };
struct host { unsigned caps;struct device *parent; };
struct mmc_card { struct host *host;bool mmc; };
struct mmc_blk_data { struct { struct mmc_card *card; } queue; };
struct disk { void *private_data; };
struct block_device { struct disk *bd_disk; };
struct mmc_ioc_cmd {};struct mmc_ioc_multi_cmd {};
static bool wingray;static int raw_calls;
static bool of_machine_is_compatible(const char *v) {assert(!strcmp(v,"motorola,wingray"));return wingray;}
static bool mmc_card_mmc(struct mmc_card *c) {return c->mmc;}
static bool of_property_read_bool(struct device_node *n,const char *v) {
 if(!n)return false;
 if(!strcmp(v,"motorola,xoom-bigpart"))return n->bigpart;
 assert(!strcmp(v,"motorola,xoom-firstboot-ro"));return n->firstboot;
}
static int mmc_blk_ioctl_cmd(struct block_device *b,struct mmc_ioc_cmd *p) {(void)b;(void)p;++raw_calls;return 11;}
static int mmc_blk_ioctl_multi_cmd(struct block_device *b,struct mmc_ioc_multi_cmd *p) {(void)b;(void)p;++raw_calls;return 12;}
'''
main=r'''
int main(void) {
 struct device_node node;struct device dev={&node};struct host host={1,&dev};
 struct mmc_card card={&host,true};struct mmc_blk_data md={ {&card} };
 struct disk disk={&md};struct block_device b={&disk};
 for(unsigned bits=0;bits<64;++bits) {
  wingray=!!(bits&1);card.mmc=!!(bits&2);host.caps=!!(bits&4);
  host.parent=(bits&8)?&dev:NULL;node.bigpart=!!(bits&16);node.firstboot=!!(bits&32);
  bool expected=bits==63;assert(mmc_wingray_firstboot_ro(&card)==expected);
  raw_calls=0;
  assert(mmc_blk_ioctl(&b,0,MMC_IOC_CMD,0)==(expected?-EROFS:11));
  assert(mmc_blk_ioctl(&b,0,MMC_IOC_MULTI_CMD,0)==(expected?-EROFS:12));
  assert(raw_calls==(expected?0:2));
  assert(mmc_blk_ioctl(&b,0,999,0)==-EINVAL);
 }
 wingray=card.mmc=true;host.caps=1;host.parent=&dev;dev.of_node=NULL;
 assert(!mmc_wingray_firstboot_ro(&card));
 puts("PASS actual first-boot gate: all 64 scope combinations; raw single/multi commands denied before dispatch only in the protected profile; null DT safe.");
}
'''
# Existing immutable md policy is assigned before queue/disk exposure, and the
# existing force_ro store cannot clear it. Do not test against a real disk.
assignment=source.index('if (mmc_wingray_firstboot_ro(card))')
assert assignment < source.index('set_disk_ro(md->disk, md->read_only || default_ro)',assignment)
assert 'set_disk_ro(dev_to_disk(dev), set || md->read_only);' in source
with tempfile.TemporaryDirectory(prefix='xoom-readonly-') as temp:
 p=Path(temp);(p/'test.c').write_text(fixture+actual+main)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined','-O2',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
