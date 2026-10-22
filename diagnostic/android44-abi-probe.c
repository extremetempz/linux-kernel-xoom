/* SPDX-License-Identifier: GPL-2.0
 * Pre-init Android4.4 ABI gate: RAM logger/ashmem, sockets and fixed block
 * protection probes. No Binder transactions, mounts, block writes or valid
 * raw MMC commands. Device execution remains untested. */
#define BINDER_IPC_32BIT 1
#ifndef XOOM_ABI_RELEASE
#define XOOM_ABI_RELEASE "4.4.147-wingray-android44"
#endif
#include <linux/types.h>
typedef __kernel_pid_t pid_t;
typedef __kernel_uid32_t uid_t;
typedef __kernel_size_t size_t;
#include <linux/android/binder.h>
#include <linux/fs.h>
#include <linux/major.h>
#include <linux/mmc/ioctl.h>
#include "uapi/ashmem.h"
#include "logger.h"

_Static_assert(BINDER_CURRENT_PROTOCOL_VERSION == 7, "Installed KitKat ABI");
_Static_assert(sizeof(struct binder_write_read) == 24, "Legacy32 write/read ABI");
_Static_assert(sizeof(struct flat_binder_object) == 16, "Legacy32 object ABI");

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
    if(code)line("XOOM_ANDROID44_ABI_FAILED\n");
    call6(1,code,0,0,0,0,0);
    for(;;) { }
}
static int equal(const char *a,const char *b)
{
    unsigned int i=0;
    while(a[i] && a[i]==b[i])++i;
    return a[i]==b[i];
}
static char uts[6][65];
static struct binder_version version;
static char ashmem_name[ASHMEM_NAME_LEN]="xoom-android44-abi-only";
static char log_buffer[128];
static int log_version=2;
static const char log_message[]="\x04XoomABI\0RAM-only ABI gate\0";
static const char * const block_paths[]={
    "/dev/mmcblk0","/dev/mmcblk0p1","/dev/mmcblk0p2","/dev/mmcblk0p3",
    "/dev/mmcblk0p4","/dev/mmcblk0p5","/dev/mmcblk0p6","/dev/mmcblk0p7",
    "/dev/mmcblk0p8","/dev/mmcblk0p9","/dev/mmcblk0p10"
};
static int logger_roundtrip(long fd,unsigned int header)
{
    unsigned int i;
    long count;
    if(call6(4,fd,(long)log_message,sizeof(log_message)-1,0,0,0)!=sizeof(log_message)-1)
        return 0;
    count=call6(3,fd,(long)log_buffer,sizeof(log_buffer),0,0,0);
    if(count!=(long)(header+sizeof(log_message)-1) ||
       ((unsigned char)log_buffer[0] | ((unsigned char)log_buffer[1]<<8))!=sizeof(log_message)-1)
        return 0;
    for(i=0;i<sizeof(log_message)-1;++i)
        if(log_buffer[header+i]!=log_message[i])return 0;
    return 1;
}
void _start(void) __attribute__((noreturn));
void _start(void)
{
    long fd, address;
    volatile unsigned int *memory;
    unsigned int i;
    if(call6(122,(long)uts,0,0,0,0,0)<0 ||
       !equal(uts[2],XOOM_ABI_RELEASE))end(1);
    /* Opening with O_WRONLY does not write. Never use O_TRUNC or a write
     * syscall on these descriptors, even if a protection defect admits one. */
    for(i=0;i<sizeof(block_paths)/sizeof(block_paths[0]);++i) {
        fd=call6(5,(long)block_paths[i],1,0,0,0,0);
        if(fd>=0)call6(6,fd,0,0,0,0,0);
        if(fd!=-30)end(12); /* require EROFS */
    }
    fd=call6(5,(long)block_paths[0],0,0,0,0,0);
    if(fd<0)end(13);
    /* Invalid NULL payloads cannot describe an MMC command. The profile must
     * reject them before decode (EROFS), not merely fail copy_from_user. */
    if(call6(54,fd,MMC_IOC_CMD,0,0,0,0)!=-30 ||
       call6(54,fd,MMC_IOC_MULTI_CMD,0,0,0,0)!=-30)end(14);
    /* Also reject generic read-only-flag changes before payload decoding.
     * NULL cannot request clearing protection, even on an unguarded kernel. */
    if(call6(54,fd,BLKROSET,0,0,0,0)!=-30)end(15);
    call6(6,fd,0,0,0,0,0);
    line("XOOM_ANDROID44_BLOCK_WRITE_OPENS_RAW_AND_ROSET_REJECTED\n");
    fd=call6(5,(long)"/dev/binder",2,0,0,0,0);
    if(fd<0)end(2);
    if(call6(54,fd,BINDER_VERSION,(long)&version,0,0,0)<0 ||
       version.protocol_version!=7)end(3);
    call6(6,fd,0,0,0,0,0);
    line("XOOM_ANDROID44_BINDER_VERSION 7\n");
    fd=call6(5,(long)"/dev/log_main",2|0x800,0,0,0,0);
    if(fd<0)end(10);
    if(call6(54,fd,LOGGER_GET_VERSION,0,0,0,0)!=1 ||
       !logger_roundtrip(fd,20) ||
       call6(54,fd,LOGGER_SET_VERSION,(long)&log_version,0,0,0)<0 ||
       call6(54,fd,LOGGER_GET_VERSION,0,0,0,0)!=2 ||
       !logger_roundtrip(fd,24))end(11);
    call6(6,fd,0,0,0,0,0);
    line("XOOM_ANDROID44_LOGGER_V1_V2_OK\n");
    fd=call6(5,(long)"/dev/ashmem",2,0,0,0,0);
    if(fd<0)end(4);
    if(call6(54,fd,ASHMEM_SET_NAME,(long)ashmem_name,0,0,0)<0 ||
       call6(54,fd,ASHMEM_SET_SIZE,4096,0,0,0)<0 ||
       call6(54,fd,ASHMEM_GET_SIZE,0,0,0,0)!=4096)end(5);
    address=call6(192,0,4096,3,1,fd,0);
    if((unsigned long)address>=(unsigned long)-4095)end(6);
    memory=(volatile unsigned int *)address;
    for(i=0;i<1024;++i)memory[i]=i^0x584d0030U;
    for(i=0;i<1024;++i)if(memory[i]!=(i^0x584d0030U))end(7);
    call6(91,address,4096,0,0,0,0);call6(6,fd,0,0,0,0,0);
    line("XOOM_ANDROID44_ASHMEM_PRIVATE_PAGE_OK\n");
    fd=call6(281,1,1,0,0,0,0); /* AF_UNIX, SOCK_STREAM */
    if(fd<0)end(8);
    call6(6,fd,0,0,0,0,0);
    fd=call6(281,16,2,15,0,0,0); /* AF_NETLINK, DGRAM, KOBJECT_UEVENT */
    if(fd<0)end(9);
    call6(6,fd,0,0,0,0,0);
    line("XOOM_ANDROID44_UNIX_UEVENT_SOCKETS_OK\nXOOM_ANDROID44_ABI_PASSED\n");
    end(0);
}
