"""Run the actual Linux cpio FSM with inert filesystem stubs and varied flush sizes."""
from pathlib import Path
import gzip,subprocess,tempfile
r=Path(__file__).resolve().parents[1]
s=(r/'sources/kernel-donor/init/initramfs.c').read_text();s=s[s.index('static ssize_t __init xwrite'):s.index('static unsigned long my_inptr')]
a=s.index('static long __init do_utime');b=s.index('static __initdata time_t mtime',a)
s=s[:a]+'''static long do_utime(char *n,time_t t){return 0;}\nstatic void dir_add(const char *n,time_t t){}\n'''+s[b:]
prefix=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <limits.h>
#include <assert.h>
#define __init
#define __initdata
#define GFP_KERNEL 0
#define kmalloc(n,f) malloc(n)
#define kfree free
#define kstrdup(n,f) strdup(n)
#define MKDEV(a,b) (((a)<<8)|(b))
#define new_encode_dev(x) (x)
#define simple_strtoul strtoul
#define panic(...) abort()
typedef mode_t umode_t;
static ssize_t sys_write(int f,const char *b,size_t n){return n;}
static int sys_link(const char*a,const char*b){return 0;}
static int sys_newlstat(const char*a,struct stat*s){return -ENOENT;}
static int sys_rmdir(const char*a){return 0;}
static int sys_unlink(const char*a){return 0;}
static int sys_open(const char*a,int f,umode_t m){return 1;}
static int sys_fchown(int a,uid_t u,gid_t g){return 0;}
static int sys_fchmod(int a,umode_t m){return 0;}
static int sys_ftruncate(int a,unsigned long n){return 0;}
static int sys_mkdir(const char*a,umode_t m){return 0;}
static int sys_chown(const char*a,uid_t u,gid_t g){return 0;}
static int sys_chmod(const char*a,umode_t m){return 0;}
static int sys_mknod(const char*a,umode_t m,unsigned d){return 0;}
static int sys_close(int a){return 0;}
static int sys_symlink(const char*a,const char*b){return 0;}
static int sys_lchown(const char*a,uid_t u,gid_t g){return 0;}
'''
main=r'''
int main(int argc,char**argv){assert(argc==3);FILE*f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);char*buf=malloc(n);assert(fread(buf,1,n,f)==n);fclose(f);header_buf=malloc(110);name_buf=malloc(N_ALIGN(PATH_MAX));symlink_buf=malloc(PATH_MAX+N_ALIGN(PATH_MAX)+1);state=Start;size_t chunk=strtoul(argv[2],NULL,0);for(size_t p=0;p<n;p+=chunk){size_t l=n-p<chunk?n-p:chunk;assert(flush_buffer(buf+p,l)==l);if(message){fprintf(stderr,"ERROR %s offset %lld state %d remaining %lu chunk %zu\n",message,(long long)this_header,state,body_len,p);return 1;}}assert(state==Reset);puts("PASS actual kernel streaming cpio parser");}
'''
with tempfile.TemporaryDirectory() as t:
 t=Path(t);(t/'fixture.c').write_text(prefix+s+main)
 archive=gzip.decompress((r/'artifacts/gpu-startup51-ready/ramdisk.cpio.gz').read_bytes())
 (t/'archive').write_bytes(archive)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=undefined',str(t/'fixture.c'),'-o',str(t/'fixture')],check=True)
 for chunk in (32768,4096,113,len(archive)):
  subprocess.run([str(t/'fixture'),str(t/'archive'),str(chunk)],check=True)
 corrupt=bytearray(archive);corrupt[0]=ord('X');(t/'corrupt').write_bytes(corrupt)
 rejected=subprocess.run([str(t/'fixture'),str(t/'corrupt'),'32768'],capture_output=True)
 assert rejected.returncode==1 and b'no cpio magic' in rejected.stderr
 print('PASS corrupt archive rejected; this fixture tests parser state, not kernel decompression or filesystem behavior')
