#!/usr/bin/env python3
"""Run actual probe control flow with a syscall fixture; no hardware claim.
ARM compilation separately checks the actual Decatf ABI widths.
"""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'diagnostic/nvmap-allocator-probe.c').read_text()
a=s.index('static long call6('); b=s.index('static void line(',a)
s=s[:a]+'static long call6(long,long,long,long,long,long,long);\n'+s[b:]
s=re.sub(r'_Static_assert\([^;]+;', '', s)
s=s.replace('__asm__ volatile("dmb sy":::"memory");','')
s=s.replace('_start','probe_start')
fixture=r'''
#include <assert.h>
#include <setjmp.h>
#include <string.h>
#include <stdio.h>
static jmp_buf escape;
static unsigned memory[65536/4], live, pinned, mapped, cycles, operation, fault;
static int status;
static char output[4096];
static long call6(long n,long a,long b,long c,long d,long e,long f) {
 (void)d;(void)e;(void)f;
 if(n==1){status=a;longjmp(escape,1);}
 if(n==122){strcpy(uts[2],fault==1?"wrong":"4.4.147-wingray-legacy-resources");return 0;}
 if(n==4){assert(a==1);strncat(output,(char*)b,c);return c;}
 if(n==5){assert(!strcmp((char*)a,"/dev/nvmap")&&b==2);return fault==2?-2:7;}
 if(n==6){assert(a==7);return 0;}
 if(n==192){assert(live&&pinned&&!mapped&&b==65536&&c==3&&d==1&&e==7);if(fault==9)return -12;mapped=1;return (long)memory;}
 if(n==91){assert(mapped);mapped=0;return 0;}
 assert(n==54&&a==7);
 if(b==NVMAP_IOC_FREE){assert(live&&!mapped&&!pinned);live=0;cycles++;return 0;}
 if(b==NVMAP_IOC_UNPIN_MULT){assert(pinned);pinned=0;return 0;}
 operation++;
 if(fault==100+operation)return -5;
 if(b==NVMAP_IOC_CREATE){assert(!live);((struct nvmap_create_handle*)c)->handle=0x1000;live=1;return 0;}
 assert(live);
 if(b==NVMAP_IOC_ALLOC){struct nvmap_alloc_handle *p=(void*)c;assert(p->heap_mask==1&&p->flags==0&&p->align==4096);return 0;}
 if(b==NVMAP_IOC_PARAM){struct nvmap_handle_param *p=(void*)c;
 p->result=p->param==1?(fault==3?4096:65536):p->param==4?(fault==4?2:1):(fault==8?0x30001000:0x30000000);return 0;}
 if(b==NVMAP_IOC_PIN_MULT){assert(!pinned);pinned=1;((struct nvmap_pin_handle*)c)->addr=fault==5?0x2ffff000:fault==6?0x3ffff000:fault==7?0x30000001:0x30000000;return 0;}
 if(b==NVMAP_IOC_MMAP){assert(mapped);return fault==10?-22:0;}
 if(b==NVMAP_IOC_CACHE){struct nvmap_cache_op *p=(void*)c;assert(mapped&&p->len==65536&&p->op==2);if(fault==11)memory[100]^=1;return 0;}
 assert(0);return -1;
}
int main(void){
 unsigned faults[]={0,1,2,3,4,5,6,7,8,9,10,11,101,102,103,104,105,106,107,108,109};
 for(unsigned i=0;i<sizeof(faults)/sizeof(*faults);i++){
  fault=faults[i];live=pinned=mapped=cycles=operation=0;output[0]=0;
  if(!setjmp(escape))probe_start();
  assert(!live&&!pinned&&!mapped);
  if(!fault){assert(status==0&&cycles==4&&strstr(output,"ALLOCATOR_PASSED"));}
  else {assert(status!=0&&strstr(output,"ALLOCATOR_FAILED")&&!strstr(output,"ALLOCATOR_PASSED"));}
 }
 puts("PASS 21 probe success/fault/cleanup paths; host fixtures only");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'probe.c';p.write_text('#include <stddef.h>\n'+s+fixture)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-I',str(root/'sources/kernel-donor/drivers/staging/tegra/video/nvmap'),str(p),'-o',t+'/test'],check=True)
 subprocess.run([t+'/test'],check=True)
