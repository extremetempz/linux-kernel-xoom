#!/usr/bin/env python3
"""Compile actual scoped backlight policy; mock SMBus with injected failures."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'sources/kernel-donor/drivers/video/backlight/lp855x_bl.c').read_text()
def extract(name):
 start=s.index('static int '+name+'(');op=s.index('{',start);end=op+1;depth=1
 while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[start:end]+'\n'
actual=''.join(extract(n) for n in ['lp855x_wingray_setup','lp855x_wingray_verify','lp855x_wingray_brightness'])
fixture=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8;
#define ARRAY_SIZE(x) ((int)(sizeof(x)/sizeof((x)[0])))
#define min(a,b) ((a)<(b)?(a):(b))
#define LP8550 0
#define dev_err(dev,fmt,...) ((void)(dev))
#define dev_info(dev,fmt,...) ((void)(dev))
struct device_node { bool custom,supply; };
struct device { struct device_node *of_node; };
struct pdata { unsigned device_control,period_ns,size_program; };
struct lp855x { struct device *dev;int chip_id;struct pdata *pdata;bool wingray_p3;void *client; };
static bool wingray;
static int regs[256],fail_read,fail_write,nreads,nwrites,wr_reg[4],wr_value[4];
static bool of_device_is_compatible(struct device_node *n,const char *v) {assert(!strcmp(v,"motorola,wingray-p3-lp8550"));return n&&n->custom;}
static bool of_machine_is_compatible(const char *v) {assert(!strcmp(v,"motorola,wingray"));return wingray;}
static void *of_find_property(struct device_node *n,const char *v,void *unused) {(void)unused;assert(!strcmp(v,"power-supply"));return n&&n->supply?n:NULL;}
static int i2c_smbus_read_byte_data(void *c,int reg) {(void)c;++nreads;return nreads==fail_read?-EIO:regs[reg];}
static int lp855x_write_byte(struct lp855x *lp,u8 reg,u8 value) {(void)lp;wr_reg[nwrites]=reg;wr_value[nwrites++]=value;assert(nwrites<=2);return nwrites==fail_write?-EIO:0;}
'''
main=r'''
static void reset(void) {nreads=nwrites=fail_read=fail_write=0;}
int main(void) {
 struct device_node node={true,true};struct device dev={&node};struct pdata pd={3,0,0};struct lp855x lp={&dev,LP8550,&pd,false,NULL};wingray=true;
 assert(lp855x_wingray_setup(&lp)==0&&lp.wingray_p3);
 for(unsigned gate=0;gate<6;++gate) {
  node.custom=node.supply=wingray=true;pd.device_control=3;pd.period_ns=pd.size_program=0;lp.chip_id=LP8550;lp.wingray_p3=false;
  if(gate==0)node.custom=false;if(gate==1)wingray=false;if(gate==2)node.supply=false;if(gate==3)lp.chip_id=1;if(gate==4)pd.period_ns=1;if(gate==5)pd.size_program=1;
  int ret=lp855x_wingray_setup(&lp);assert(!lp.wingray_p3);assert(ret==(gate==0?0:-EINVAL));
 }
 node.custom=node.supply=wingray=true;pd.device_control=4;pd.period_ns=pd.size_program=0;lp.chip_id=LP8550;assert(lp855x_wingray_setup(&lp)==-EINVAL);
 static const int prod[]={0x67,0xbf,0x3f,0x08,0xea,0x64,0x2a};regs[3]=0xfc;for(int i=0;i<7;++i)regs[0xa1+i]=prod[i];reset();assert(lp855x_wingray_verify(&lp)==0&&nreads==8&&nwrites==0);
 for(int fail=1;fail<=8;++fail) {reset();fail_read=fail;assert(lp855x_wingray_verify(&lp)==-EIO&&nreads==fail&&nwrites==0);}
 for(int i=0;i<8;++i) {int reg=i?0xa0+i:3;int old=regs[reg];regs[reg]^=1;reset();assert(lp855x_wingray_verify(&lp)<0&&nwrites==0);regs[reg]=old;}
 for(unsigned br=0;br<=255;++br) {
  reset();assert(lp855x_wingray_brightness(&lp,br)==0);
  if(!br)assert(nwrites==1&&wr_reg[0]==1&&wr_value[0]==4);
  else {assert(nwrites==2&&wr_reg[0]==0xa0&&(unsigned)wr_value[0]==br*726/1000&&wr_value[0]<=185&&wr_reg[1]==1&&wr_value[1]==3);}
  for(int fail=1;fail<=(br?2:1);++fail) {reset();fail_write=fail;assert(lp855x_wingray_brightness(&lp,br)==-EIO&&nwrites==fail);}
 }
 reset();assert(!lp855x_wingray_brightness(&lp,~0U)&&wr_value[0]==185);
 puts("PASS actual backlight policy: strict scope/supply/config gates, production-read validation and failures, 256 brightness values, 19mA cap policy, write-failure stop and overflow clamp.");
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-backlight-') as t:
 p=Path(t);(p/'test.c').write_text(fixture+actual+main)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=undefined','-O2',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
