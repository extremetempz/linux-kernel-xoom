#!/usr/bin/env python3
"""Reproduce image59's missing fbmem with Linux's actual OF range mapper."""
from pathlib import Path
import subprocess,tempfile,sys,struct
r=Path(__file__).resolve().parents[1];s=(r/'sources/kernel-donor/drivers/of/address.c').read_text();a=s.index('static u64 of_bus_default_map(');b=s.index('\nstatic int of_bus_default_translate',a)
prefix='''#include <assert.h>
#include <stdint.h>
#include <arpa/inet.h>
typedef uint32_t __be32;typedef uint64_t u64;
#define OF_BAD_ADDR (~(u64)0)
#define pr_debug(...) ((void)0)
static u64 of_read_number(const __be32 *p,int n){u64 v=0;while(n--)v=(v<<32)|ntohl(*p++);return v;}
'''
main='''
static u64 mapped(uint32_t addr,int fixed){
 __be32 a=htonl(addr);__be32 old[]={htonl(0x54000000),htonl(0x54000000),htonl(0x04000000)};
 __be32 fb[]={htonl(0x2e800000),htonl(0x2e800000),htonl(0x00800000)};
 u64 offset=of_bus_default_map(&a,old,1,1,1);
 if(offset!=OF_BAD_ADDR)return 0x54000000+offset;
 if(fixed){offset=of_bus_default_map(&a,fb,1,1,1);if(offset!=OF_BAD_ADDR)return 0x2e800000+offset;}
 return OF_BAD_ADDR;
}
int main(void){
 assert(mapped(0x54200000,0)==0x54200000);
 assert(mapped(0x2e800000,0)==OF_BAD_ADDR); /* old count loop stops before fbmem */
 assert(mapped(0x2e800000,1)==0x2e800000);
 assert(mapped(0x2effffff,1)==0x2effffff);
 assert(mapped(0x2e7fffff,1)==OF_BAD_ADDR);
 assert(mapped(0x2f000000,1)==OF_BAD_ADDR);
 assert(mapped(0x30000000,1)==OF_BAD_ADDR); /* generic nvmap heap is not exposed */
 assert(mapped(0x54140000,1)==mapped(0x54140000,0));
 assert(mapped(0x54180000,1)==mapped(0x54180000,0));
 return 0;
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'test.c').write_text(prefix+s[a:b]+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p/'test.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
print('PASS actual Linux OF mapper: image59 drops fbmem; exact 8MiB map translates both bounds and excludes neighbors/nvmap heap; engine MMIO unchanged')
