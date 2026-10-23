#!/usr/bin/env python3
"""Actual cached-sharing probe flow under syscall mocks; not cache hardware evidence."""
from pathlib import Path
import subprocess,tempfile,re
root=Path(__file__).resolve().parents[1]
s=(root/'diagnostic/nvmap-cached-sharing-probe.c').read_text()
a=s.index('static long call6(');b=s.index('static void line(',a)
s=s[:a]+'static long call6(long,long,long,long,long,long,long);\n'+s[b:]
s=re.sub(r'_Static_assert\([^;]+;', '', s).replace('__asm__ volatile("dmb sy":::"memory");','').replace('_start','probe_start')
fixture=r'''
#include <assert.h>
#include <setjmp.h>
#include <string.h>
#include <stdio.h>
static jmp_buf escape;
static unsigned memory[65536/4], refs[16], pins[16], opens[16], mapped, opened, operation, fail_at, variant, passed_ops;
static int status; static char output[4096];
static long call6(long n,long a,long b,long c,long d,long e,long f) {
 (void)f;
 if(n==1){status=a;longjmp(escape,1);}
 if(n==4){assert(a==1);strncat(output,(char*)b,c);return c;}
 if(n==122){strcpy(uts[2],variant==1?"wrong":"4.4.147-wingray-legacy-resources");return 0;}
 if(n==6){assert(a>=7&&a<16&&opens[a]);assert(!refs[a]&&!pins[a]);opens[a]=0;return 0;}
 if(n==91){assert(mapped&&a==(long)memory&&b==65536);mapped--;return 0;}
 if(n==54 && b==NVMAP_IOC_FREE){assert(refs[a]&&!pins[a]);refs[a]=0;return 0;}
 if(n==54 && b==NVMAP_IOC_UNPIN_MULT){assert(refs[a]&&pins[a]);pins[a]=0;return 0;}
 operation++;
 if(operation==fail_at)return -5;
 if(n==5){assert(!strcmp((char*)a,"/dev/nvmap")&&b==2);long fd=7+opened++;assert(fd<16);opens[fd]=1;return fd;}
 if(n==192){assert(opens[e]&&refs[e]&&pins[e]&&b==65536&&c==3&&d==1);mapped++;return (long)memory;}
 assert(n==54&&a>=7&&a<16&&opens[a]);
 if(b==NVMAP_IOC_CREATE){assert(!refs[a]);refs[a]=1;((struct nvmap_create_handle*)c)->handle=0x1000;return 0;}
 if(b==NVMAP_IOC_FROM_ID){struct nvmap_create_handle *p=(void*)c;assert(p->id==0x1000&&!refs[a]&&refs[a-1]);p->handle=0x1000;refs[a]=1;return 0;}
 assert(refs[a]);
 if(b==NVMAP_IOC_GET_ID){((struct nvmap_create_handle*)c)->id=0x1000;return 0;}
 if(b==NVMAP_IOC_ALLOC){struct nvmap_alloc_handle *p=(void*)c;assert(p->heap_mask==1&&p->flags==3&&p->align==4096);return 0;}
 if(b==NVMAP_IOC_PARAM){struct nvmap_handle_param *p=(void*)c;p->result=p->param==1?(variant==2?4096:65536):p->param==4?(variant==3?2:1):0x30000000;return 0;}
 if(b==NVMAP_IOC_PIN_MULT){struct nvmap_pin_handle *p=(void*)c;assert(!pins[a]);pins[a]=1;p->addr=variant==4?0x2ffff000:variant==5?0x3ffff000:variant==6?0x30000001:variant==7&&a==8?0x30001000:0x30000000;return 0;}
 if(b==NVMAP_IOC_MMAP){struct nvmap_map_caller *p=(void*)c;assert(p->flags==3&&p->length==65536&&p->offset==0&&p->addr==(unsigned long)memory);return 0;}
 if(b==NVMAP_IOC_CACHE){struct nvmap_cache_op *p=(void*)c;assert(mapped&&p->len==65536&&p->op>=0&&p->op<=2);if(variant==8)memory[123]^=1;return 0;}
 assert(0);return -1;
}
static void run(unsigned fail,unsigned kind){
 memset(refs,0,sizeof(refs));memset(pins,0,sizeof(pins));memset(opens,0,sizeof(opens));output[0]=0;mapped=opened=operation=0;fail_at=fail;variant=kind;
 if(!setjmp(escape))probe_start();
 assert(!mapped);for(unsigned i=0;i<16;i++)assert(!refs[i]&&!pins[i]&&!opens[i]);
 if(!fail&&!kind){assert(status==0&&strstr(output,"CACHED_SHARING_PASSED"));passed_ops=operation;}
 else assert(status!=0&&strstr(output,"CACHED_SHARING_FAILED")&&!strstr(output,"CACHED_SHARING_PASSED"));
}
int main(void){run(0,0);unsigned n=passed_ops;for(unsigned i=1;i<=n;i++)run(i,0);for(unsigned i=1;i<=8;i++)run(0,i);printf("PASS %u cached-sharing success/fault/cleanup fixture cases; hardware pending\n",n+9);}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(s+fixture)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-I',str(root/'sources/kernel-donor/drivers/staging/tegra/video/nvmap'),str(p),'-o',t+'/test'],check=True)
 subprocess.run([t+'/test'],check=True)
