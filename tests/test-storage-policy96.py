#!/usr/bin/env python3
"""Compile actual helper/ioctl/bio-policy functions with faulted fake devices."""
from pathlib import Path
import subprocess,tempfile
R=Path(__file__).resolve().parents[1];K=R/'sources/kernel-donor'
def function(s,name):
 p=s.index(name+'(');a=s.rfind('\n',0,p)+1;b=s.index('{',p);e=b+1;d=1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]+'\n'
helper=r'''
#define STORAGE_POLICY_TEST
#include <assert.h>
#include <string.h>
#include <errno.h>
static int board=1,marker=1,inspect,backup,firstboot,approval=1,cache;
static int policy[2],fail_set,fail_get,wrong_get,bad_size,fail_open,fail_close,sets,gets,opens,closes;
long call6(long,long,long,long,long,long,long);
'''+('#include "'+str(R/'diagnostic/storage-policy.c')+'"\n')+r'''
long call6(long n,long a,long b,long c,long d,long e,long f){
 (void)d;(void)e;(void)f;
 if(n==4)return c;
 if(n==5){const char *p=(void*)a;opens++;
  if(!strcmp(p,"/dev/mmcblk0p10"))return fail_open==1?-ENOENT:10;
  if(!strcmp(p,"/dev/mmcblk0p9"))return fail_open==2?-ENOENT:9;
  if(strstr(p,"compatible"))return 100;
  int yes=strstr(p,"firstboot-ro")?firstboot:strstr(p,"persistent-storage")?marker:
    strstr(p,"storage-inspect")?inspect:strstr(p,"storage-backup")?backup:
    strstr(p,"data-approved")?approval:strstr(p,"cache-approved")?cache:0;
  return yes?101:-ENOENT;
 }
 if(n==3){const char *v=board?"motorola,wingray\0nvidia,tegra20":"samsung,p4wifi\0";
  int z=board?30:16;memcpy((void*)b,v,z);return z;}
 if(n==6){closes++;return a==fail_close?-EIO:0;}
 assert(n==54&&(a==9||a==10));int i=a==10?0:1;
 if(b==BLKGETSIZE64){*(unsigned long long*)c=bad_size?512:(i==0?30334779392ULL:536870912ULL);return 0;}
 if(b==BLKROSET){sets++;int value=*(int*)c;if(fail_set==a&&value==0)return -EIO;policy[i]=value;return 0;}
 assert(b==BLKROGET&&c);gets++;if(fail_get==a&&policy[i]==0)return -EFAULT;
 *(int*)c=wrong_get==a?1:policy[i];return 0;
}
static void reset(void){board=marker=approval=1;inspect=backup=firstboot=cache=0;
 policy[0]=policy[1]=1;fail_set=fail_get=wrong_get=bad_size=fail_open=fail_close=sets=gets=opens=closes=0;}
int main(void){
 reset();assert(storage_policy()==0&&policy[0]==0&&policy[1]==1);
 int old=sets;assert(storage_policy()!=0&&sets==old&&policy[0]==0); /* repeat refuses, no borrowed ownership */
 reset();cache=1;assert(storage_policy()==0&&!policy[0]&&!policy[1]);
 for(int x=0;x<6;x++){reset();switch(x){case 0:board=0;break;case 1:marker=0;break;case 2:inspect=1;break;
 case 3:backup=1;break;case 4:firstboot=1;break;case 5:approval=0;break;}
 assert(storage_policy()!=0&&!sets&&policy[0]&&policy[1]);}
 reset();bad_size=1;assert(storage_policy()!=0&&!sets);
 reset();fail_open=1;assert(storage_policy()!=0&&!sets);
 reset();cache=1;fail_open=2;assert(storage_policy()!=0&&!sets&&policy[0]);
 for(int x=0;x<3;x++){reset();cache=1;switch(x){case 0:fail_set=9;break;case 1:fail_get=9;break;case 2:wrong_get=9;break;}
 assert(storage_policy()!=0&&policy[0]&&policy[1]);}
 reset();fail_close=10;assert(storage_policy()!=0&&policy[0]);
 return 0;
}
'''
gen=(K/'block/genhd.c').read_text();io=(K/'block/ioctl.c').read_text();mmc=(K/'drivers/mmc/card/block.c').read_text();bio=(K/'block/blk-core.c').read_text()
kernel=r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <linux/fs.h>
#include <linux/blkpg.h>
#define MMC_IOC_CMD 0x12345
#define MMC_IOC_MULTI_CMD 0x12346
#define FMODE_WRITE 2
#define GENHD_FL_WINGRAY_STORAGE_RO 1024
#define REQ_WRITE 1
#define REQ_DISCARD 2
#define REQ_WRITE_SAME 4
#define __user
#define get_user(n,p) ((p)?((n)=*(p),0):-EFAULT)
typedef int fmode_t;
struct hd_struct {unsigned partno;int policy;};struct card {int unused;};
struct mmc_blk_data {struct {struct card *card;} queue;};
struct gendisk {void *private_data;int flags;};
struct block_device {struct gendisk *bd_disk;struct hd_struct *bd_part;};
struct bio {struct block_device *bi_bdev;int bi_rw;};
static bool persistent=true,firstboot,admin=true;
static bool mmc_wingray_persistent_storage(struct card *c){(void)c;return persistent;}
static bool mmc_wingray_firstboot_ro(struct card *c){(void)c;return firstboot;}
static int mmc_blk_ioctl_cmd(struct block_device *b,void *v){(void)b;(void)v;return 42;}
static int mmc_blk_ioctl_multi_cmd(struct block_device *b,void *v){(void)b;(void)v;return 43;}
#define ENOIOCTLCMD 515
#define CAP_SYS_ADMIN 1
static bool capable(int cap){(void)cap;return admin;}
'''+function(mmc,'mmc_blk_ioctl')+r'''
static int __blkdev_driver_ioctl(struct block_device *b,fmode_t mode,unsigned cmd,unsigned long arg){return mmc_blk_ioctl(b,mode,cmd,arg);}
'''+function(io,'is_unrecognized_ioctl')+function(gen,'set_device_ro')+function(gen,'bdev_read_only')+function(io,'blkdev_roset')+function(bio,'wingray_storage_write_blocked')+r'''
int main(void){
 struct mmc_blk_data md={0};struct gendisk disk={&md,1024};struct hd_struct p={0,1};struct block_device b={&disk,&p};
 int zero=0,one=1;
 for(unsigned i=0;i<=10;i++){p.partno=i;p.policy=1;
 int ret=blkdev_roset(&b,0,BLKROSET,(unsigned long)&zero);
 assert((ret==0)==(i==9||i==10));assert(bdev_read_only(&b)==!(i==9||i==10));
 assert(mmc_blk_ioctl(&b,0,MMC_IOC_CMD,0)==-EROFS);
 assert(mmc_blk_ioctl(&b,0,MMC_IOC_MULTI_CMD,0)==-EROFS);
 assert(mmc_blk_ioctl(&b,0,BLKPG,0)==-EROFS);
 assert(mmc_blk_ioctl(&b,0,BLKRRPART,0)==-EROFS);
 struct bio bio={&b,REQ_WRITE};assert(wingray_storage_write_blocked(&bio)==!(i==9||i==10));
 assert(blkdev_roset(&b,0,BLKROSET,(unsigned long)&one)==0&&bdev_read_only(&b));
 for(int op=1;op<=4;op*=2){bio.bi_rw=op;assert(wingray_storage_write_blocked(&bio));}
 bio.bi_rw=0;assert(!wingray_storage_write_blocked(&bio));
 }
 p.partno=10;admin=false;assert(blkdev_roset(&b,0,BLKROSET,(unsigned long)&zero)==-EACCES&&p.policy);
 admin=true;assert(blkdev_roset(&b,0,BLKROSET,0)==-EROFS);
 firstboot=true;assert(blkdev_roset(&b,0,BLKROSET,(unsigned long)&zero)==-EROFS);
 firstboot=persistent=false;disk.flags=0;p.policy=1;struct bio bio={&b,REQ_WRITE};assert(!wingray_storage_write_blocked(&bio));
 return 0;
}
'''
with tempfile.TemporaryDirectory() as t:
 for name,code in [('helper',helper),('kernel',kernel)]:
  p=Path(t)/name;p.with_suffix('.c').write_text(code)
  subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined',str(p.with_suffix('.c')),'-o',str(p)],check=True)
  subprocess.run([str(p)],check=True)
assert bio.index('wingray_storage_write_blocked(bio)')<bio.index('blk_partition_remap(bio)',bio.index('generic_make_request_checks('))
print('PASS actual ARM-helper logic and kernel partition/ioctl/bio paths; no physical I/O')
