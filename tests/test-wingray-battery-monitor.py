#!/usr/bin/env python3
"""Compile actual monitoring policy/sample/property code with faulted hardware IO."""
from pathlib import Path
import re, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
K=ROOT/'sources/kernel-donor'
source=(K/'drivers/power/wingray_battery_monitor.c').read_text()
def function(name):
    start=source.index('static ',source.index(name)-35)
    brace=source.index('{',start);end=brace+1;depth=1
    while depth:
        if source[end]=='{':depth+=1
        elif source[end]=='}':depth-=1
        end+=1
    return source[start:end]+'\n'
header=(K/'drivers/power/wingray_battery_monitor.h').read_text()
w1=(K/'drivers/w1/slaves/w1_ds2781.h').read_text()
defines='\n'.join(line for line in w1.splitlines() if line.startswith('#define DS2781_'))
code=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <string.h>
#include <stdint.h>
typedef uint8_t u8;
enum power_supply_property {POWER_SUPPLY_PROP_ONLINE,POWER_SUPPLY_PROP_STATUS,POWER_SUPPLY_PROP_PRESENT,POWER_SUPPLY_PROP_CAPACITY,POWER_SUPPLY_PROP_VOLTAGE_NOW,POWER_SUPPLY_PROP_CURRENT_NOW,POWER_SUPPLY_PROP_TEMP};
enum {POWER_SUPPLY_STATUS_UNKNOWN,POWER_SUPPLY_STATUS_CHARGING,POWER_SUPPLY_STATUS_DISCHARGING,POWER_SUPPLY_STATUS_NOT_CHARGING,POWER_SUPPLY_STATUS_FULL};
enum {POWER_SUPPLY_TYPE_BATTERY,POWER_SUPPLY_TYPE_MAINS};
union power_supply_propval {int intval;};
struct power_supply_desc {int type;};
struct power_supply {struct power_supply_desc *desc;void *data;};
struct device {};
struct wingray_monitor {struct device *w1_dev;struct power_supply *battery,*ac;int lock,gpio[3];int error,current_error,online,status,capacity,uv,ua,temp;};
static u8 regs[256];static int gpio_levels[3],error,short_read,rsns_error,reads;
static int gpio_get_value_cansleep(int gpio){return gpio_levels[gpio];}
static int w1_ds2781_io(struct device *dev,u8 *buf,int addr,int len,int write){(void)dev;assert(!write);reads++;if(error)return error;if(addr==0x69&&rsns_error)return rsns_error;memcpy(buf,regs+addr,len);return short_read?len-1:len;}
#define dev_warn_ratelimited(...) ((void)0)
static void mutex_lock(int *p){(void)p;}
static void mutex_unlock(int *p){(void)p;}
static void *power_supply_get_drvdata(struct power_supply *p){return p->data;}
'''+defines+'\n'+header+'\n'+function('wingray_read')+function('wingray_sample')+function('wingray_get')+r'''
int main(void){
 struct wingray_monitor m={.gpio={0,1,2}};
 struct power_supply_desc bd={POWER_SUPPLY_TYPE_BATTERY},ad={POWER_SUPPLY_TYPE_MAINS};
 struct power_supply bat={&bd,&m},ac={&ad,&m};union power_supply_propval v;
 int online;
 assert(wingray_charge_status(1,1,0,&online)==POWER_SUPPLY_STATUS_DISCHARGING&&!online);
 assert(wingray_charge_status(1,1,1,&online)==POWER_SUPPLY_STATUS_NOT_CHARGING&&online);
 assert(wingray_charge_status(0,1,1,&online)==POWER_SUPPLY_STATUS_CHARGING&&online);
 assert(wingray_charge_status(1,0,1,&online)==POWER_SUPPLY_STATUS_FULL&&online);
 assert(wingray_charge_status(0,0,1,&online)==POWER_SUPPLY_STATUS_UNKNOWN&&online);
 assert(wingray_charge_status(0,1,0,&online)==POWER_SUPPLY_STATUS_CHARGING&&online);
 assert(wingray_charge_status(1,0,0,&online)==POWER_SUPPLY_STATUS_FULL&&online);
 assert(wingray_charge_status(0,0,0,&online)==POWER_SUPPLY_STATUS_UNKNOWN&&online);
 assert(wingray_voltage_uv(100,0)==7808000);
 assert(wingray_temperature_dc(25,0)==250);
 assert(wingray_temperature_dc(255,0)==-10);
 assert(wingray_temperature_dc(255,224)==-1);
 assert(wingray_current_ua(0,64,100)==10000);
 assert(wingray_current_ua(255,192,100)==-10000);
 regs[DS2781_RARC]=67;regs[DS2781_VOLT_MSB]=100;regs[DS2781_TEMP_MSB]=25;
 regs[DS2781_RSNSP]=100;regs[DS2781_CURRENT_LSB]=64;
 gpio_levels[0]=gpio_levels[1]=1;
 wingray_sample(&m);assert(!m.error&&!m.current_error);
 assert(!wingray_get(&bat,POWER_SUPPLY_PROP_CAPACITY,&v)&&v.intval==67);
 /* Registration may invoke get_property before m.ac has been assigned. */
 assert(!wingray_get(&ac,POWER_SUPPLY_PROP_ONLINE,&v)&&!v.intval);
 gpio_levels[2]=1;wingray_sample(&m);
 assert(!wingray_get(&bat,POWER_SUPPLY_PROP_STATUS,&v)&&v.intval==POWER_SUPPLY_STATUS_NOT_CHARGING);
 error=-EIO;wingray_sample(&m);assert(wingray_get(&bat,POWER_SUPPLY_PROP_CAPACITY,&v)==-EIO);
 assert(!wingray_get(&ac,POWER_SUPPLY_PROP_ONLINE,&v)&&v.intval==1);
 error=0;short_read=1;wingray_sample(&m);assert(m.error==-EIO);short_read=0;
 regs[DS2781_RARC]=255;wingray_sample(&m);assert(m.error==-ERANGE);
 regs[DS2781_RARC]=67;regs[DS2781_VOLT_MSB]=0;wingray_sample(&m);assert(m.error==-ERANGE);
 regs[DS2781_VOLT_MSB]=100;regs[DS2781_RSNSP]=0;wingray_sample(&m);
 assert(!m.error&&wingray_get(&bat,POWER_SUPPLY_PROP_CURRENT_NOW,&v)==-ENODATA);
 assert(!wingray_get(&bat,POWER_SUPPLY_PROP_CAPACITY,&v)&&v.intval==67);
 rsns_error=-ETIMEDOUT;wingray_sample(&m);assert(m.current_error==-ETIMEDOUT);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
    p=Path(d);(p/'test.c').write_text(code)
    subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
# Monitoring-only invariants: no charger outputs, EEPROM or register writes.
for forbidden in ('gpio_direction_output','gpio_set_value','w1_ds2781_eeprom_cmd','W1_DS2781_WRITE_DATA','set_property'):
    assert forbidden not in source,forbidden
assert 'devm_gpio_request_one(&pdev->dev, m->gpio[i], GPIOF_IN' in source
assert 'ret == len ? 0' in source
lower=(K/'drivers/w1/slaves/w1_ds2781.c').read_text()
assert 'return -ENODEV;' in lower and lower.count('return -EPERM;')==2
master=(K/'drivers/w1/masters/tegra_w1.c').read_text()
assert 'dev->bus_master.read_block = tegra_w1_read_block;' in master
assert master.index('w1_remove_master_device') < master.index('free_irq',master.index('static int tegra_w1_remove'))
print('PASS actual battery units/status/property functions: 8 charger states, signed current/temp, read errors, short reads, invalid capacity/voltage, missing RSNS; monitoring-only guards')
