#!/usr/bin/env python3
"""Compile actual cache helper with injected syscall failures; never touches devices."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
code=r'''
#define STORAGE_POLICY_TEST
#include <assert.h>
#include <string.h>
#include <errno.h>
static int ro=1, badsize, board=1, marker=1, data, badset, badget, sets;
long call6(long,long,long,long,long,long,long);
'''+f'#include "{ROOT}/diagnostic/cache99-policy.c"\n'+r'''
long call6(long n,long a,long b,long c,long d,long e,long f) {
 (void)d;(void)e;(void)f;
 if(n==4)return c;
 if(n==5) {
  const char *p=(void*)a;
  if(!strcmp(p,"/dev/mmcblk0p9"))return 9;
  assert(strncmp(p,"/dev/",5));
  if(strstr(p,"compatible"))return 100;
  if(strstr(p,"data-approved"))return data?101:-ENOENT;
  return marker?101:-ENOENT;
 }
 if(n==3){const char *s=board?"motorola,wingray\0":"samsung,p4wifi\0";int len=board?17:15;memcpy((void*)b,s,len);return len;}
 if(n==6)return 0;
 assert(n==54&&a==9);
 if(b==BLKGETSIZE64){*(unsigned long long*)c=badsize?512:536870912ULL;return 0;}
 if(b==BLKROGET){if(badget&&ro==0)return -EIO;*(int*)c=ro;return 0;}
 assert(b==BLKROSET);sets++;if(badset&&*(int*)c==0)return -EIO;ro=*(int*)c;return 0;
}
int main(void){
 assert(cache_policy()==0);
#ifdef CACHE_LOCK_ONLY
 assert(ro==1);
 ro=0;assert(cache_policy()==0&&ro==1);
#else
 assert(ro==0);int before=sets;assert(cache_policy()!=0&&sets==before);
 ro=1;badset=1;assert(cache_policy()!=0&&ro==1);badset=0;
 badget=1;assert(cache_policy()!=0&&ro==1);badget=0;
#endif
 ro=1;sets=0;badsize=1;assert(cache_policy()!=0&&sets==0);badsize=0;
 board=0;assert(cache_policy()!=0&&sets==0);board=1;
 marker=0;assert(cache_policy()!=0&&sets==0);marker=1;
 data=1;assert(cache_policy()!=0&&sets==0);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'fixture.c';p.write_text(code)
 for mode in ('release','lock'):
  args=['cc','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=undefined']
  if mode=='lock':args+=['-DCACHE_LOCK_ONLY']
  exe=Path(d)/mode;subprocess.run([*args,str(p),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('PASS actual p9-only release/relock helpers and uncertain ioctl rollback')
