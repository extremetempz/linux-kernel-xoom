#!/usr/bin/env python3
"""Fault-test the real Decatf nvmap DT parser with bounded OF/provider stubs.

No device access. ARM object compilation is a separate gate; host fixtures
exercise ownership/error paths, not the kernel's OF implementation itself.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PATH = 'drivers/staging/tegra/video/nvmap/nvmap_dev.c'
source = (ROOT / 'sources/kernel-donor' / PATH).read_text()


def function(text, name):
    end = text.index('\n}', text.index(name + '(')) + 2
    start = text.rfind('\nstatic ', 0, text.index(name + '(')) + 1
    return text[start:end]


PRELUDE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
typedef uint32_t u32, __be32, phys_addr_t;
#define BITS_PER_LONG 32
#define BIT(i) (1UL<<(i))
#define GFP_KERNEL 0
#define PAGE_SHIFT 12
#define NVMAP_HEAP_CARVEOUT_MASK 0x3fffffffU
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define dev_err(...) ((void)0)
struct resource {uint64_t start,end;const char *name;};
struct device_node {
 const char *full_name;
 struct device_node *parent,*region,*next,*children;
 bool available,no_map,reusable,reg_bad,has_region,has_buddy,buddy_bad,usage_bad;
 int phandle_len,refs;
 struct resource mem;
 u32 usage,buddy;
};
struct device {struct device_node *of_node;};
struct platform_device {struct device dev;};
struct nvmap_platform_carveout {const char *name;u32 usage_mask;phys_addr_t base;uint32_t size,buddy_size;};
struct nvmap_platform_data {struct nvmap_platform_carveout *carveouts;unsigned nr_carveouts;};
static bool wingray;
static int allocs,fail_alloc,removes,fail_remove;
static unsigned long mapped_pfn;
static bool pfn_valid(unsigned long pfn) {return pfn==mapped_pfn;}
static void *allocations[8];
static struct device_node *get(struct device_node *n) {if(n)n->refs++;return n;}
static void of_node_put(struct device_node *n) {if(n){assert(n->refs>0);n->refs--;}}
static struct device_node *of_get_parent(struct device_node *n) {return get(n->parent);}
static bool of_machine_is_compatible(const char *s) {assert(!strcmp(s,"motorola,wingray"));return wingray;}
static bool of_device_is_available(struct device_node *n) {return n->available;}
static bool of_property_read_bool(struct device_node *n,const char *s) {
 if(!strcmp(s,"no-map"))return n->no_map;
 assert(!strcmp(s,"reusable"));return n->reusable;
}
static const void *of_get_property(struct device_node *n,const char *s,int *len) {
 assert(!strcmp(s,"memory-region"));*len=n->phandle_len;return n->has_region?n:NULL;
}
static struct device_node *of_parse_phandle(struct device_node *n,const char *s,int i) {
 assert(!strcmp(s,"memory-region")&&!i);return get(n->region);
}
static const void *of_find_property(struct device_node *n,const char *s,int *unused) {
 assert(!strcmp(s,"buddy-size")&&!unused);return n->has_buddy?n:NULL;
}
static int of_property_read_u32(struct device_node *n,const char *s,u32 *out) {
 if(!strcmp(s,"usage-mask")){if(n->usage_bad)return -EINVAL;*out=n->usage;return 0;}
 assert(!strcmp(s,"buddy-size"));if(n->buddy_bad)return -EINVAL;*out=n->buddy;return 0;
}
static struct device_node *of_get_child_by_name(struct device_node *n,const char *s) {
 assert(!strcmp(s,"carveouts"));return get(n->children);
}
static unsigned of_get_available_child_count(struct device_node *n) {
 unsigned count=0;for(n=n->children;n;n=n->next)count+=n->available;return count;
}
static struct device_node *next_available(struct device_node *p,struct device_node *old) {
 struct device_node *n=old?old->next:p->children;of_node_put(old);
 for(;n&&!n->available;n=n->next){} return get(n);
}
#define for_each_available_child_of_node(p,c) for(c=next_available(p,NULL);c;c=next_available(p,c))
static int of_address_to_resource(struct device_node *n,int i,struct resource *r) {
 assert(!i);if(n->reg_bad)return -EINVAL;*r=n->mem;return 0;
}
static uint64_t resource_size(const struct resource *r) {return r->end-r->start+1;}
static bool resource_contains(struct resource *a,struct resource *b) {return a->start<=b->start&&a->end>=b->end;}
static bool is_power_of_2(u32 x) {return x&&!(x&(x-1));}
static void *allocate(unsigned long count,unsigned long size) {
 void *p;if(++allocs==fail_alloc)return NULL;p=calloc(count,size);assert(p);allocations[allocs]=p;return p;
}
static void *devm_kzalloc(struct device *d,unsigned long s,int f) {(void)d;(void)f;return allocate(1,s);}
static void *devm_kcalloc(struct device *d,unsigned long c,unsigned long s,int f) {(void)d;(void)f;return allocate(c,s);}
static int memblock_remove(phys_addr_t base,uint32_t size) {
 assert(size&&base);return ++removes==fail_remove?-EIO:0;
}
/* Model the target's size_t width in the extracted parser's casts. */
#define size_t uint32_t
'''

MAIN = r'''
#undef size_t
static struct device_node root,bus,carveouts,n[2],r[2],reserved;
static struct platform_device pdev;
static void setup(bool target) {
 unsigned i;
 memset(&root,0,sizeof(root));memset(&bus,0,sizeof(bus));memset(&carveouts,0,sizeof(carveouts));
 memset(n,0,sizeof(n));memset(r,0,sizeof(r));memset(&reserved,0,sizeof(reserved));
 allocs=removes=fail_alloc=fail_remove=0;wingray=target;
 mapped_pfn=~0UL;
 root.full_name="/";bus.full_name="/nvmap";bus.children=&carveouts;
 carveouts.full_name="/nvmap/carveouts";carveouts.children=n;
 reserved.full_name="/reserved-memory";reserved.available=true;
 n[0].mem=(struct resource){0x40000400,0x4003ffff,"iram"};
 n[1].mem=(struct resource){0x30000000,0x3fffffff,"generic-0"};
 for(i=0;i<2;i++) {
  n[i].available=true;n[i].full_name=i?"generic-0":"iram";
  n[i].has_region=true;n[i].phandle_len=4;n[i].region=&r[i];
  n[i].usage=i?1:0x20000000;n[i].has_buddy=true;n[i].buddy=i?0x8000:0;
  r[i].parent=&reserved;r[i].mem=n[i].mem;r[i].available=true;r[i].no_map=true;
 }
 n[0].next=&n[1];pdev.dev.of_node=&bus;
}
static void verify(int expected,unsigned count,int removed) {
 struct nvmap_platform_data *data=nvmap_parse_dt(&pdev);
 unsigned i;
 if(expected)assert(IS_ERR(data)&&PTR_ERR(data)==expected);
 else {assert(!IS_ERR(data));assert(data->nr_carveouts==count);}
 assert(removes==removed);
 assert(!root.refs&&!bus.refs&&!carveouts.refs&&!reserved.refs);
 for(i=0;i<2;i++)assert(!n[i].refs&&!r[i].refs);
 for(i=0;i<8;i++){free(allocations[i]);allocations[i]=NULL;}
}
int main(void) {
 unsigned i;
 setup(true);verify(0,2,0);
 setup(false);n[0].has_region=n[1].has_region=false;verify(0,2,2);
 setup(true);n[0].available=false;verify(0,1,0);
 setup(true);n[0].available=n[1].available=false;verify(-EINVAL,0,0);
 setup(true);bus.children=NULL;verify(-EINVAL,0,0);
 for(i=1;i<=2;i++){setup(true);fail_alloc=i;verify(-ENOMEM,0,0);}
 setup(false);n[0].has_region=false;n[1].reg_bad=true;verify(-EINVAL,0,0);
 for(i=0;i<2;i++) {
  setup(true);n[i].has_region=false;verify(-EINVAL,0,0);
  setup(true);n[i].phandle_len=8;verify(-EINVAL,0,0);
  setup(true);n[i].region=NULL;verify(-EINVAL,0,0);
  setup(true);r[i].parent=NULL;verify(-EINVAL,0,0);
  setup(true);reserved.full_name="/other";verify(-EINVAL,0,0);
  setup(true);reserved.available=false;verify(-EINVAL,0,0);
  setup(true);r[i].available=false;verify(-EINVAL,0,0);
  setup(true);r[i].no_map=false;verify(-EINVAL,0,0);
  setup(true);r[i].reusable=true;verify(-EINVAL,0,0);
  setup(true);r[i].reg_bad=true;verify(-EINVAL,0,0);
  setup(true);r[i].mem.end--;verify(-EINVAL,0,0);
  setup(true);n[i].mem.end=n[i].mem.start-1;verify(-EINVAL,0,0);
  setup(true);n[i].mem.end=UINT64_MAX;verify(-EINVAL,0,0);
  setup(true);n[i].mem.start=0x100000000ULL;n[i].mem.end=0x10000ffffULL;verify(-EINVAL,0,0);
  setup(true);n[i].usage=0;verify(-EINVAL,0,0);
  setup(true);n[i].usage=0x80000000U;verify(-EINVAL,0,0);
  setup(true);n[i].usage_bad=true;verify(-EINVAL,0,0);
  setup(true);n[i].buddy_bad=true;verify(-EINVAL,0,0);
 }
 setup(true);n[1].mem=n[0].mem;verify(-EINVAL,0,0);
 setup(true);n[1].buddy=3;verify(-EINVAL,0,0);
 setup(true);n[1].buddy=0x20000000;verify(-EINVAL,0,0);
 setup(true);n[1].mem.start++;verify(-EINVAL,0,0);
 setup(true);n[1].mem.end--;verify(-EINVAL,0,0);
 setup(false);n[0].has_region=n[1].has_region=false;fail_remove=1;verify(-EIO,0,1);
 setup(true);mapped_pfn=0x30000;verify(-EINVAL,0,0);
 setup(true);mapped_pfn=0x38000;verify(-EINVAL,0,0);
 setup(true);mapped_pfn=0x3ffff;verify(-EINVAL,0,0);
 puts("PASS actual nvmap DT parser: reserved ownership, malformed resources, overlap, allocation/errors and OF references; no hardware accessed.");
}
'''

with tempfile.TemporaryDirectory(prefix='xoom-nvmap-dt-test-') as temp:
    path = Path(temp) / 'test.c'
    path.write_text(PRELUDE + function(source, 'nvmap_dt_reserved') + '\n' +
                    function(source, 'nvmap_parse_dt') + '\n' + MAIN)
    binary = Path(temp) / 'test'
    subprocess.run(['cc', '-std=gnu99', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined,address', '-fno-omit-frame-pointer',
                    str(path), '-o', str(binary)], check=True)
    # LeakSanitizer cannot attach under this runner's ptrace sandbox. Explicit
    # fixture cleanup/refcount checks remain active, as do ASan and UBSan.
    subprocess.run([str(binary)], check=True,
                   env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
