#!/usr/bin/env python3
"""Compile the actual bounded initrd fingerprint and cookie-52 rootfs branch."""
from pathlib import Path
import runpy,subprocess,tempfile
r=Path(__file__).resolve().parents[1]
base=runpy.run_path(str(r/'tests/test-gpu-initrd-trace.py'))
s=(r/'sources/kernel-donor/init/initramfs.c').read_text();a=s.index('static u32 __init wingray_initrd_fingerprint');b=s.index('\n#endif',a);fingerprint=s[a:b]
prefix=base['prefix'].replace('0x584d0051','0x584d0052')+'\ntypedef uint32_t u32;\n#define pr_info(...) ((void)0)\n'
prefix='#include <stdint.h>\n#include <stdlib.h>\n'+prefix
main=r'''
int main(int argc,char**argv){assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);unsigned long n=ftell(f);rewind(f);unsigned char*buf=malloc(n);assert(buf&&fread(buf,1,n,f)==n);fclose(f);
 assert(wingray_initrd_fingerprint((const unsigned char*)"",0)==0x811c9dc5U);
 assert(wingray_initrd_fingerprint((const unsigned char*)"foobar",6)==0xbf9cf968U);
 initrd_start=(unsigned long)buf;initrd_end=initrd_start+n;external_error="junk in compressed archive";
 if(!setjmp(escape)){populate_rootfs();assert(0);}char expected[128];snprintf(expected,sizeof(expected),"RD %08x %08lx",wingray_initrd_fingerprint(buf,n),n);assert(strlen(expected)==20&&!strcmp(panic_text,expected));assert(unpack_calls==2&&!loaded);
 unsigned old=wingray_initrd_fingerprint(buf,n);buf[n/2]^=1;assert(wingray_initrd_fingerprint(buf,n)!=old);buf[n/2]^=1;
 initrd_start=(unsigned long)buf;initrd_end=initrd_start+16*1024*1024+1;unpack_calls=0;
 if(!setjmp(escape)){populate_rootfs();assert(0);}assert(!strcmp(panic_text,"XOOM initrd bad size")&&unpack_calls==1);
 initrd_start=(unsigned long)buf;initrd_end=initrd_start+n;external_error=NULL;assert(!populate_rootfs());assert(freed==1&&loaded==1);free(buf);
 puts("PASS actual cookie-52 fingerprint: known vectors, changed input, bounded length, complete retained metadata and success path");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+fingerprint+base['body']+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True)
 subprocess.run([t+'/test',str(r/'artifacts/gpu-startup51-ready/ramdisk.cpio.gz')],check=True)
 p.write_text((prefix+fingerprint+base['body']+main).replace('#define CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE 0x584d0052','#define CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE 0x584d0053'))
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable','-fsanitize=undefined',str(p),'-o',t+'/test53'],check=True)
 subprocess.run([t+'/test53',str(r/'artifacts/gpu-startup51-ready/ramdisk.cpio.gz')],check=True)
