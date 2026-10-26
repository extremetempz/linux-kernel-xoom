#!/usr/bin/env python3
"""Exercise actual DS2781 IO guards and Tegra short-read propagation."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];K=ROOT/'sources/kernel-donor'
def get(s,name):
    pos=s.index(name+'(')
    start=s.rfind('\n',0,pos)+1
    brace=s.index('{',pos);end=brace+1;depth=1
    while depth:
        depth+=(s[end]=='{')-(s[end]=='}');end+=1
    return s[start:end]+'\n'
lower=(K/'drivers/w1/slaves/w1_ds2781.c').read_text()
master=(K/'drivers/w1/masters/tegra_w1.c').read_text()
code=r'''
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <assert.h>
#include <errno.h>
#include <string.h>
typedef uint8_t u8;
#define DS2781_DATA_SIZE 0xb2
#define W1_DS2781_WRITE_DATA 0x6c
#define W1_DS2781_READ_DATA 0x69
#define CONFIG_BATTERY_WINGRAY_MONITOR 1
#define IS_ENABLED(x) (x)
#define min_t(type,a,b) ((type)(a)<(type)(b)?(type)(a):(type)(b))
#define container_of(p,type,member) ((type*)((char*)(p)-offsetof(type,member)))
struct device {int unused;};
struct w1_master {int bus_mutex;};
struct w1_slave {struct device dev;struct w1_master *master;};
static int wingray=1,reset_error,writes,blocks,read_count=2;
static int of_machine_is_compatible(const char *name){(void)name;return wingray;}
static int w1_reset_select_slave(struct w1_slave *p){(void)p;return reset_error;}
static void w1_write_8(struct w1_master *p,int data){(void)p;(void)data;writes++;}
static void w1_write_block(struct w1_master *p,const char *buf,int n){(void)p;(void)buf;(void)n;blocks++;}
static int w1_read_block(struct w1_master *p,char *buf,int n){(void)p;memset(buf,0x12,n);return read_count;}
static void mutex_lock(int *p){(void)p;}
static void mutex_unlock(int *p){(void)p;}
struct tegra_device {bool io_failed;};
static int touch_calls,fail_at;
static u8 tegra_w1_touch_bit(void *p,u8 bit){struct tegra_device *d=p;assert(bit==1);if(++touch_calls==fail_at)d->io_failed=true;return 1;}
'''+get(lower,'w1_ds2781_do_io')+get(lower,'w1_ds2781_io')+get(lower,'w1_ds2781_eeprom_cmd')+get(master,'tegra_w1_read_block')+r'''
int main(void){struct w1_master bus={0};struct w1_slave slave={{0},&bus};char buf[2]={0};
 assert(w1_ds2781_io(0,buf,0,2,0)==-ENODEV);
 assert(w1_ds2781_io(&slave.dev,buf,0,2,1)==-EPERM&&!writes&&!blocks);
 assert(w1_ds2781_eeprom_cmd(&slave.dev,0x60,0x48)==-EPERM&&!writes);
 reset_error=1;assert(w1_ds2781_io(&slave.dev,buf,0,2,0)==-ENODEV&&!writes);
 reset_error=0;assert(w1_ds2781_io(&slave.dev,buf,-1,2,0)==-EINVAL);
 assert(w1_ds2781_io(&slave.dev,buf,0,2,0)==2&&writes==2);
 read_count=1;assert(w1_ds2781_io(&slave.dev,buf,0,2,0)==1);
 wingray=0;writes=0;assert(w1_ds2781_io(&slave.dev,buf,0,2,1)==2&&blocks==1&&writes==2);
 struct tegra_device dev={false};u8 data[2];
 assert(tegra_w1_read_block(&dev,data,2)==2&&data[0]==255&&data[1]==255);
 touch_calls=0;fail_at=10;assert(tegra_w1_read_block(&dev,data,2)==0&&dev.io_failed);
 return 0;}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['cc','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS actual DS2781 transport: null/reset/bounds/short-read errors, EEPROM/write veto before bus IO, other boards unchanged, Tegra read fault propagation')
