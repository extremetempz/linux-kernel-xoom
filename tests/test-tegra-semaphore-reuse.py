#!/usr/bin/env python3
"""Exercise existing Decatf semaphore operations with mocked allocation/waiting."""
from pathlib import Path
import re,subprocess,tempfile
source=(Path(__file__).resolve().parents[1]/'sources/kernel-donor/drivers/staging/tegra/media/avp/trpc_sema.c').read_text()
def function(name):
 a=re.search(r'^int (?:__init )?'+name+r'\(',source,re.M).start();e=source.index('{',a)+1;d=1
 while d:d+=(source[e]=='{')-(source[e]=='}');e+=1
 return source[a:e]
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#define __init
#define GFP_KERNEL 0
#define MAX_SCHEDULE_TIMEOUT 1000000000L
#define MISC_MAJOR 10
#define pr_err(...) ((void)0)
#define pr_info(...) ((void)0)
typedef int wait_queue_head_t;typedef int spinlock_t;
struct file;
struct tegra_sema_info {struct file*file;wait_queue_head_t wq;spinlock_t lock;int count;};
static unsigned long jiffies=100;
static int alloc_fail,wait_result,reg_error,registrations;
static void*kzalloc(size_t n,int flags){(void)flags;return alloc_fail?NULL:calloc(1,n);}
#define kfree(p) free(p)
#define init_waitqueue_head(p) (*(p)=0)
#define spin_lock_init(p) (*(p)=0)
#define spin_lock_irqsave(l,f) do{assert(!*(l));*(l)=1;(f)=0;}while(0)
#define spin_unlock_irqrestore(l,f) do{assert(*(l));*(l)=0;(void)(f);}while(0)
#define wake_up_interruptible_all(p) ((void)(p))
#define msecs_to_jiffies(t) (t)
#define jiffies_to_msecs(t) (t)
#define time_before(a,b) ((long)((a)-(b))<0)
#define wait_event_interruptible_timeout(w,c,t) ((void)(w),(void)(t),(c)?1:wait_result)
struct miscdevice{int minor;};static struct miscdevice trpc_sema_misc_device;
static int rpc_sema_minor=-1;
static int misc_register(struct miscdevice*d){registrations++;if(reg_error)return reg_error;d->minor=42;return 0;}
'''
main=r'''
int main(void){struct tegra_sema_info*p=NULL;long timeout;
 alloc_fail=1;assert(tegra_sema_open(&p)==-ENOMEM&&!p);alloc_fail=0;
 assert(!tegra_sema_open(&p)&&p&&!p->count&&!p->lock);
 assert(tegra_sema_signal(NULL)==-EINVAL);
 timeout=0;assert(tegra_sema_wait(p,&timeout)==-ETIMEDOUT&&!timeout);
 assert(!tegra_sema_signal(p)&&!tegra_sema_signal(p)&&p->count==2);
 timeout=0;assert(!tegra_sema_wait(p,&timeout)&&p->count==1);
 timeout=10;assert(!tegra_sema_wait(p,&timeout)&&!p->count);
 timeout=10;wait_result=-512;assert(tegra_sema_wait(p,&timeout)==-EINTR&&timeout==10);
 assert(!tegra_sema_release(p));
 reg_error=-EIO;assert(trpc_sema_init()==-EIO&&rpc_sema_minor==-1);
 reg_error=0;assert(!trpc_sema_init()&&rpc_sema_minor==42);
 assert(trpc_sema_init()==-EBUSY&&registrations==2);
 puts("PASS existing semaphore functions: allocation failure, counting, timeout/interruption, registration failure and duplicate-init rejection (UBSan)");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+'\n'.join(function(n) for n in ['tegra_sema_signal','tegra_sema_wait','tegra_sema_open','tegra_sema_release','trpc_sema_init'])+main)
 subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
