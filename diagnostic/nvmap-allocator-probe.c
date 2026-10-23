/* SPDX-License-Identifier: GPL-2.0
 * Bounded CPU-only carveout smoke test. Uses Decatf's actual ioctl header.
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
static int test(long fd) {
 struct nvmap_create_handle create={.size=BYTES};
 struct nvmap_alloc_handle alloc={0,1,0,4096}; /* generic only, uncached */
 struct nvmap_pin_handle pin={0,0,1};
 struct nvmap_handle_param param={0,NVMAP_HANDLE_PARAM_SIZE,0};
 struct nvmap_map_caller map={0,0,BYTES,0,0};
 struct nvmap_cache_op cache={0,0,BYTES,NVMAP_CACHE_OP_WB_INV};
 long address=-1; int pinned=0,code=1; unsigned i,round;
 volatile unsigned *memory;
 line("NVMAP_STAGE_CREATE\n");
 if(ctl(fd,NVMAP_IOC_CREATE,&create)<0 || !create.handle)return 1;
 alloc.handle=create.handle; param.handle=create.handle; pin.handles=create.handle;
 map.handle=create.handle; cache.handle=create.handle;
 line("NVMAP_STAGE_ALLOC\n");
 if(ctl(fd,NVMAP_IOC_ALLOC,&alloc)<0)goto out;
 if(ctl(fd,NVMAP_IOC_PARAM,&param)<0 || param.result!=BYTES)goto out;
 param.param=NVMAP_HANDLE_PARAM_HEAP;
 if(ctl(fd,NVMAP_IOC_PARAM,&param)<0 || param.result!=1)goto out;
 line("NVMAP_STAGE_PIN\n");
 if(ctl(fd,NVMAP_IOC_PIN_MULT,&pin)<0)goto out;
 pinned=1;
 if(pin.addr<0x30000000UL || pin.addr>0x40000000UL-BYTES || (pin.addr&4095))goto out;
 param.param=NVMAP_HANDLE_PARAM_BASE;
 if(ctl(fd,NVMAP_IOC_PARAM,&param)<0 || param.result!=pin.addr)goto out;
 line("NVMAP_STAGE_MAP\n");
 address=call6(192,0,BYTES,3,1,fd,0); /* mmap2, shared, driver VMA */
 if((unsigned long)address>=(unsigned long)-4095){address=-1;goto out;}
 map.addr=(unsigned long)address; cache.addr=map.addr;
 if(ctl(fd,NVMAP_IOC_MMAP,&map)<0)goto out;
 memory=(volatile unsigned *)address;
 for(round=0;round<2;round++) {
  for(i=0;i<BYTES/4;i++)memory[i]=(i*0x10201U)^0x584f4f4dU^(round*0xffffffffU);
  __asm__ volatile("dmb sy":::"memory");
  if(ctl(fd,NVMAP_IOC_CACHE,&cache)<0)goto out;
  for(i=0;i<BYTES/4;i++)if(memory[i]!=((i*0x10201U)^0x584f4f4dU^(round*0xffffffffU)))goto out;
 }
 line("NVMAP_CPU_PATTERN_AND_CACHE_IOCTL_OK\n");
 code=0;
out:
 if(address!=-1 && call6(91,address,BYTES,0,0,0,0)<0)code=1;
 if(pinned && ctl(fd,NVMAP_IOC_UNPIN_MULT,&pin)<0)code=1;
 if(call6(54,fd,NVMAP_IOC_FREE,create.handle,0,0,0)<0)code=1;
 return code;
}
void _start(void) __attribute__((noreturn));
void _start(void) {
 long fd; int code=1; unsigned cycle;
 if(call6(122,(long)uts,0,0,0,0,0)<0 || !same(uts[2],"4.4.147-wingray-legacy-resources"))goto done;
 fd=call6(5,(long)"/dev/nvmap",2,0,0,0,0);
 if(fd<0)goto done;
 for(cycle=0;cycle<4;cycle++)if(test(fd))goto close;
 code=0;
close:
 if(call6(6,fd,0,0,0,0,0)<0)code=1;
done:
 line(code ? "XOOM_NVMAP_ALLOCATOR_FAILED\n" : "XOOM_NVMAP_ALLOCATOR_PASSED cycles=4 bytes=65536 uncached=1\n");
 call6(1,code,0,0,0,0,0); for(;;){}
}
