/* SPDX-License-Identifier: GPL-2.0
 * Bounded cacheable, two-client carveout sharing test. Uses Decatf's actual ioctl header.
 * No GPU, IRAM, GART, display, block-device or power operations.
 */
#include <linux/types.h>
#include "nvmap_ioctl.h"
_Static_assert(sizeof(struct nvmap_create_handle)==8, "ARM32 create");
_Static_assert(sizeof(struct nvmap_map_caller)==20, "ARM32 map");
_Static_assert(sizeof(struct nvmap_pin_handle)==12, "ARM32 pin");
#define BYTES 65536U
static long call6(long n,long a,long b,long c,long d,long e,long f) {
 register long r0 __asm__("r0")=a,r1 __asm__("r1")=b,r2 __asm__("r2")=c;
 register long r3 __asm__("r3")=d,r4 __asm__("r4")=e,r5 __asm__("r5")=f,r7 __asm__("r7")=n;
 __asm__ volatile("svc 0":"+r"(r0):"r"(r1),"r"(r2),"r"(r3),"r"(r4),"r"(r5),"r"(r7):"memory","cc");
 return r0;
}
static void line(const char *s) { unsigned n=0; while(s[n])++n; call6(4,1,(long)s,n,0,0,0); }
static int same(const char *a,const char *b) { while(*a && *a==*b){a++;b++;}return *a==*b; }
static char uts[6][65];
static long ctl(long fd,unsigned request,void *p) {return call6(54,fd,request,(long)p,0,0,0);}
/* Identical cacheability on both mappings: never mix cached/uncached aliases. */
#define CACHEABLE 3U /* NVMAP_HANDLE_CACHEABLE in Decatf's nvmap.h */
struct client {long fd,address; unsigned handle; int pinned;};
static int drop(struct client *c) {
 int bad=0; struct nvmap_pin_handle p={c->handle,0,1};
 if(c->address!=-1) {if(call6(91,c->address,BYTES,0,0,0,0)<0)bad=1;c->address=-1;}
 if(c->pinned) {if(ctl(c->fd,NVMAP_IOC_UNPIN_MULT,&p)<0)bad=1;c->pinned=0;}
 if(c->handle) {if(call6(54,c->fd,NVMAP_IOC_FREE,c->handle,0,0,0)<0)bad=1;c->handle=0;}
 if(c->fd>=0) {if(call6(6,c->fd,0,0,0,0,0)<0)bad=1;c->fd=-1;}
 return bad;
}
static int maintain(struct client *c,int operation) {
 struct nvmap_cache_op op={(unsigned long)c->address,c->handle,BYTES,operation};
 __asm__ volatile("dmb sy":::"memory");
 return ctl(c->fd,NVMAP_IOC_CACHE,&op)<0;
}
static int mapping(struct client *c,unsigned long expected_base) {
 struct nvmap_pin_handle p={c->handle,0,1};
 struct nvmap_handle_param q={c->handle,NVMAP_HANDLE_PARAM_SIZE,0};
 struct nvmap_map_caller m={c->handle,0,BYTES,CACHEABLE,0};
 if(ctl(c->fd,NVMAP_IOC_PARAM,&q)<0 || q.result!=BYTES)return 1;
 q.param=NVMAP_HANDLE_PARAM_HEAP;
 if(ctl(c->fd,NVMAP_IOC_PARAM,&q)<0 || q.result!=1)return 1;
 if(ctl(c->fd,NVMAP_IOC_PIN_MULT,&p)<0)return 1;
 c->pinned=1;
 if(p.addr<0x30000000UL || p.addr>0x40000000UL-BYTES || (p.addr&4095))return 1;
 if(expected_base && p.addr!=expected_base)return 1;
 q.param=NVMAP_HANDLE_PARAM_BASE;
 if(ctl(c->fd,NVMAP_IOC_PARAM,&q)<0 || q.result!=p.addr)return 1;
 c->address=call6(192,0,BYTES,3,1,c->fd,0);
 if((unsigned long)c->address>=(unsigned long)-4095){c->address=-1;return 1;}
 m.addr=(unsigned long)c->address;
 return ctl(c->fd,NVMAP_IOC_MMAP,&m)<0;
}
static unsigned pattern(unsigned i,unsigned round){return (i*0x10201U)^0x53485244U^(round*0xffffffffU);}
static int shared_cycle(void) {
 struct client a={-1,-1,0,0},b={-1,-1,0,0};
 struct nvmap_create_handle h={.size=BYTES},shared={.id=0,.handle=0};
 struct nvmap_alloc_handle alloc={0,1,CACHEABLE,4096};
 struct nvmap_handle_param base={0,NVMAP_HANDLE_PARAM_BASE,0};
 unsigned i,round;int code=1;
 volatile unsigned *writer,*reader;
 line("NVMAP_SHARED_CREATE\n");
 a.fd=call6(5,(long)"/dev/nvmap",2,0,0,0,0);if(a.fd<0)goto out;
 if(ctl(a.fd,NVMAP_IOC_CREATE,&h)<0 || !h.handle)goto out;
 a.handle=h.handle;alloc.handle=a.handle;
 if(ctl(a.fd,NVMAP_IOC_ALLOC,&alloc)<0 || mapping(&a,0))goto out;
 base.handle=a.handle;if(ctl(a.fd,NVMAP_IOC_PARAM,&base)<0)goto out;
 shared.handle=a.handle;
 if(ctl(a.fd,NVMAP_IOC_GET_ID,&shared)<0 || !shared.id)goto out;
 line("NVMAP_SHARED_IMPORT\n");
 b.fd=call6(5,(long)"/dev/nvmap",2,0,0,0,0);if(b.fd<0)goto out;
 shared.handle=0;
 if(ctl(b.fd,NVMAP_IOC_FROM_ID,&shared)<0 || !shared.handle)goto out;
 b.handle=shared.handle;
 if(mapping(&b,base.result))goto out;
 writer=(volatile unsigned*)a.address;reader=(volatile unsigned*)b.address;
 for(round=0;round<2;round++) {
  for(i=0;i<BYTES/4;i++)writer[i]=pattern(i,round);
  if(maintain(&a,NVMAP_CACHE_OP_WB) || maintain(&b,NVMAP_CACHE_OP_INV))goto out;
  for(i=0;i<BYTES/4;i++)if(reader[i]!=pattern(i,round))goto out;
  for(i=0;i<BYTES/4;i++)reader[i]=~pattern(i,round);
  if(maintain(&b,NVMAP_CACHE_OP_WB_INV) || maintain(&a,NVMAP_CACHE_OP_INV))goto out;
  for(i=0;i<BYTES/4;i++)if(writer[i]!=~pattern(i,round))goto out;
 }
 line("NVMAP_CACHED_TWO_CLIENT_PATTERNS_OK\n");
 if(drop(&a))goto out;
 /* Imported reference and mapping must survive release of the owner client. */
 if(maintain(&b,NVMAP_CACHE_OP_INV))goto out;
 for(i=0;i<BYTES/4;i++)if(reader[i]!=~pattern(i,1))goto out;
 for(i=0;i<BYTES/4;i++)reader[i]=pattern(i,2);
 if(maintain(&b,NVMAP_CACHE_OP_WB_INV))goto out;
 for(i=0;i<BYTES/4;i++)if(reader[i]!=pattern(i,2))goto out;
 line("NVMAP_IMPORTED_MAPPING_SURVIVES_OWNER_CLOSE_OK\n");
 code=0;
out:
 if(drop(&b))code=1;
 if(drop(&a))code=1;
 return code;
}
void _start(void) __attribute__((noreturn));
void _start(void) {
 int code=1;unsigned cycle;
 if(call6(122,(long)uts,0,0,0,0,0)<0 || !same(uts[2],"4.4.147-wingray-legacy-resources"))goto done;
 for(cycle=0;cycle<2;cycle++)if(shared_cycle())goto done;
 code=0;
done:
 line(code ? "XOOM_NVMAP_CACHED_SHARING_FAILED\n" : "XOOM_NVMAP_CACHED_SHARING_PASSED cycles=2 bytes=65536 clients=2\n");
 call6(1,code,0,0,0,0,0);for(;;){}
}
