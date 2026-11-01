/* SPDX-License-Identifier: GPL-2.0
 * Fixed-purpose Wingray persistent-storage policy helper.
 * It never writes media: it only clears BLKROSET on p9/p10 and checks the
 * resulting policy. The kernel must expose the persistent-storage DT marker;
 * this helper refuses in inspection mode or on any other board/path.
 */
#include <linux/types.h>
#include <linux/fs.h>

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

static void line(const char *s)
{
    unsigned int n=0;
    while(s[n])++n;
    call6(4,1,(long)s,n,0,0,0);
}

static void end(int code) __attribute__((noreturn));
static void end(int code)
{
    if(code)line("XOOM_STORAGE_POLICY_FAILED\n");
    call6(1,code,0,0,0,0,0);
    for(;;) { }
}

static int exists(const char *path)
{
    long fd=call6(5,(long)path,0,0,0,0,0);
    if(fd<0)return 0;
    call6(6,fd,0,0,0,0,0);
    return 1;
}

static int release(const char *path)
{
    long fd, value;
    int zero=0;
    fd=call6(5,(long)path,0,0,0,0,0);
    if(fd<0)return 1;
    if(call6(54,fd,BLKROSET,(long)&zero,0,0,0)<0)return 1;
    value=call6(54,fd,BLKROGET,0,0,0,0);
    call6(6,fd,0,0,0,0,0);
    return value!=0;
}

void _start(void) __attribute__((noreturn));
void _start(void)
{
    if(!exists("/proc/device-tree/sdhci@c8000600/motorola,xoom-persistent-storage"))
        end(1);
    if(exists("/proc/device-tree/motorola,wingray-storage-inspect"))
        end(2);
    if(release("/dev/mmcblk0p9"))end(3);
    if(release("/dev/mmcblk0p10"))end(4);
    line("XOOM_STORAGE_POLICY_P9_P10_RW\n");
    line("XOOM_STORAGE_POLICY_P0_P1_P8_RO_UNCHANGED\n");
    end(0);
}
