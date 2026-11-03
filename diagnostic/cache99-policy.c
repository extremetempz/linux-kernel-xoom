/* SPDX-License-Identifier: GPL-2.0
 * Fixed-purpose Wingray persistent-storage policy helper.
 * It never writes media: it only clears BLKROSET on p9/p10 and checks the
 * resulting policy. The kernel must expose the persistent-storage DT marker;
 * this helper refuses in inspection mode or on any other board/path.
 */
#include <stddef.h>
#include <linux/types.h>
#include <linux/fs.h>
#include <asm/fcntl.h>

#ifndef STORAGE_POLICY_TEST
static long call6(long n, long a, long b, long c, long d, long e, long f)
{
    register long r0 __asm__("r0")=a, r1 __asm__("r1")=b;
    register long r2 __asm__("r2")=c, r3 __asm__("r3")=d;
    register long r4 __asm__("r4")=e, r5 __asm__("r5")=f;
    register long r7 __asm__("r7")=n;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1),"r"(r2),"r"(r3),
                     "r"(r4),"r"(r5),"r"(r7) : "memory","cc");
    return r0;
}

#else
extern long call6(long,long,long,long,long,long,long);
#endif

static void line(const char *s)
{
    unsigned int n=0;
    while(s[n])++n;
    call6(4,1,(long)s,n,0,0,0);
}

#ifndef STORAGE_POLICY_TEST
static void end(int code) __attribute__((noreturn));
static void end(int code)
{
    if(code)line("XOOM_STORAGE_POLICY_FAILED\n");
    call6(1,code,0,0,0,0,0);
    for(;;) { }
}

#endif

static int exists(const char *path)
{
    long fd=call6(5,(long)path,0,0,0,0,0);
    if(fd<0)return 0;
    call6(6,fd,0,0,0,0,0);
    return 1;
}


/* Both fds stay open until the transaction is verified or rolled back.
 * BLKROGET returns an errno/status, and writes the flag through int *.
 */
static int set_ro(long fd, int wanted)
{
    int got = -1;
    if (call6(54,fd,BLKROSET,(long)&wanted,0,0,0) != 0) return 1;
    if (call6(54,fd,BLKROGET,(long)&got,0,0,0) != 0) return 1;
    return got != wanted;
}

static int board_ok(void)
{
    char buf[256]; long fd, n, i, j;
    const char name[]="motorola,wingray";
    fd=call6(5,(long)"/sys/firmware/devicetree/base/compatible",0,0,0,0,0);
    if(fd<0) return 0;
    n=call6(3,fd,(long)buf,sizeof(buf),0,0,0);
    if(call6(6,fd,0,0,0,0,0)!=0 || n<=0 || n==(long)sizeof(buf))return 0;
    for(i=0;i<n;) {
        for(j=0;j<(long)sizeof(name)-1 && i+j<n && buf[i+j]==name[j];j++);
        if(j==(long)sizeof(name)-1 && i+j<n && buf[i+j]==0)return 1;
        while(i<n && buf[i])i++;
        i++;
    }
    return 0;
}

/* This helper can never open p10 or the whole disk for a policy change. */
static int cache_policy(void)
{
 long fd; unsigned long long bytes=0; int rc=1;
 if (!board_ok() ||
     !exists("/sys/firmware/devicetree/base/motorola,wingray-cache-repair99") ||
     !exists("/sys/firmware/devicetree/base/sdhci@c8000600/motorola,xoom-cache-repair-only") ||
     exists("/bin/storage-data-approved")) return 1;
 fd=call6(5,(long)"/dev/mmcblk0p9",O_NOFOLLOW|O_CLOEXEC,0,0,0,0);
 if(fd<0)return 1;
 if(call6(54,fd,BLKGETSIZE64,(long)&bytes,0,0,0)==0 && bytes==536870912ULL) {
#ifdef CACHE_LOCK_ONLY
  rc=set_ro(fd,1);
#else
  int initial=-1;
  if(call6(54,fd,BLKROGET,(long)&initial,0,0,0)==0 && initial==1) {
   rc=set_ro(fd,0);
   if(rc && set_ro(fd,1))line("CACHE99_ROLLBACK_FAILED\n");
  }
#endif
 }
 if(call6(6,fd,0,0,0,0,0)!=0) {
  fd=call6(5,(long)"/dev/mmcblk0p9",O_NOFOLLOW|O_CLOEXEC,0,0,0,0);
  if(fd>=0){set_ro(fd,1);call6(6,fd,0,0,0,0,0);}
  rc=1;
 }
 return rc;
}
#ifndef STORAGE_POLICY_TEST
void _start(void) __attribute__((noreturn));
void _start(void) { end(cache_policy()); }
#endif
