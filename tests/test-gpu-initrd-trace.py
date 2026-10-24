#!/usr/bin/env python3
"""Exercise actual diagnostic RAM-root checks; no device operations."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1]
s=(r/'sources/kernel-donor/init/initramfs.c').read_text()
a=s.index('static int __init populate_rootfs(');b=s.index('\nrootfs_initcall',a)
body=s[a:b]
s=(r/'sources/kernel-donor/init/main.c').read_text();a=s.index('#if defined(CONFIG_MOTOROLA_XOOM_GPU_STARTUP_TRACE)',s.index('ramdisk_execute_command = "/init";'));b=s.index('\n#endif',a)+len('\n#endif');access=s[a:b]
prefix=r'''
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#define __init
#define __user
#define CONFIG_MOTOROLA_XOOM_GPU_STARTUP_TRACE 1
#define CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE 0x584d0051
#define WG_EXEC_RET 0x54
#define KERN_EMERG ""
#define KERN_INFO ""
#define printk(...) ((void)0)
static jmp_buf escape;static char panic_text[128];
static char __initramfs_start[1];static unsigned long __initramfs_size;
static unsigned long initrd_start,initrd_end;static int do_skip_initramfs;
static int unpack_calls,freed,loaded,access_error,marked;static char *external_error;
static char *ramdisk_execute_command="/init";
static void panic(const char*f,...){va_list a;va_start(a,f);vsnprintf(panic_text,sizeof(panic_text),f,a);va_end(a);longjmp(escape,1);}
static int default_rootfs(void){return 0;}
static char *unpack_to_rootfs(char*p,unsigned long n){(void)n;unpack_calls++;return p==__initramfs_start?NULL:external_error;}
static void free_initrd(void){freed++;initrd_start=initrd_end=0;}
static void load_default_modules(void){loaded++;}
static int sys_access(const char*p,int mode){assert(!strcmp(p,"/init")&&!mode);return access_error;}
static void wingray_gputrace_mark(int offset,int value){assert(offset==WG_EXEC_RET);marked=value;}
'''
main=r'''
static void check_access(void){
ACCESS
}
static void reset(void){initrd_start=0xc1000000;initrd_end=initrd_start+3278629;do_skip_initramfs=0;unpack_calls=freed=loaded=access_error=marked=0;external_error=NULL;panic_text[0]=0;}
int main(void){reset();assert(!populate_rootfs());assert(unpack_calls==2&&freed==1&&loaded==1);check_access();
 reset();initrd_start=0;if(!setjmp(escape)){populate_rootfs();assert(0);}assert(!strcmp(panic_text,"XOOM initrd absent")&&!unpack_calls);
 reset();do_skip_initramfs=1;if(!setjmp(escape)){populate_rootfs();assert(0);}assert(!strcmp(panic_text,"XOOM initrd skipped")&&!unpack_calls);
 reset();external_error="junk in compressed archive";if(!setjmp(escape)){populate_rootfs();assert(0);}assert(!strcmp(panic_text,"XOOM unpack junk in compressed archive")&&unpack_calls==2&&!loaded);
 reset();access_error=-2;if(!setjmp(escape)){check_access();assert(0);}assert(marked==-2&&!strcmp(panic_text,"XOOM init access -2"));
 puts("PASS actual diagnostic RAM-root branches: normal unpack, absent/skipped ramdisk, unpack failure and /init errno; no disk fallback");}
'''.replace('ACCESS',access)
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+body+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True)
 subprocess.run([t+'/test'],check=True)
