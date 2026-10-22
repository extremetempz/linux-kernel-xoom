#!/usr/bin/env python3
"""Compile real mXT init/policy code with mocked kernel call boundaries.

No I2C, firmware requests, input injection or device access occurs. The two
programming-entry tests compile the actual prefix through its first external
side effect; mocks prove the Wingray guard returns before that boundary.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'sources/kernel-donor/drivers/input/touchscreen/atmel_mxt_ts.c'
s = SOURCE.read_text()

def extract(signature):
    start = s.index(signature)
    opening = s.index('{', start)
    end, depth = opening + 1, 1
    while depth:
        depth += (s[end] == '{') - (s[end] == '}')
        end += 1
    return s[start:end] + '\n'

fixture = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <sys/types.h>
typedef unsigned char u8; typedef unsigned int u32;
typedef unsigned short umode_t;
struct device_node { bool wingray; };
struct kobject { struct device *dev; };
struct device { struct device_node *of_node; void *driver_data; struct kobject kobj; };
struct i2c_adapter { unsigned nr; };
struct i2c_client { struct device dev; struct i2c_adapter *adapter; unsigned addr,irq; const char *name; };
struct i2c_device_id { int unused; };
struct gpio_desc { int unused; };
struct regulator { int unused; };
struct mxt_platform_data { unsigned irqflags; };
struct input_dev { int unused; };
struct firmware { const char *data; size_t size; };
struct device_attribute { int unused; };
struct attribute { unsigned mode; };
static struct { struct attribute attr; } dev_attr_update_fw, dev_attr_object;
struct mxt_info { unsigned family_id,variant_id,version,build,object_num; };
struct mxt_data { struct i2c_client *client; bool in_bootloader; unsigned irq,multitouch,T9_reportid_max,T9_reportid_min,num_touchids; struct mxt_info info; const struct mxt_platform_data *pdata; char phys[64]; struct gpio_desc *reset_gpio,*enable_gpio; int bl_completion,reset_completion,crc_completion,suspend_work,suspended; };
#define MXT_TOUCH_MULTI_T9 9
#define MXT_TOUCH_MULTITOUCHSCREEN_T100 100
#define MXT_FW_RESET_TIME 3000
#define MXT_RESET_TIME 200
#define MXT_RESET_TIMEOUT 2000
#define IRQF_ONESHOT 1
#define IRQ_NOAUTOEN 4096
#define GPIOD_OUT_HIGH 1
#define GPIOD_OUT_LOW 2
#define GPIOD_ASIS 0
#define IS_ERR(p) ((intptr_t)(p)<0 && (intptr_t)(p)>-4096)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(n) ((void *)(intptr_t)(n))
#define INIT_WORK(p,fn) ((void)(p))
#define MXT_CFG_NAME "maxtouch.cfg"
#define MXT_FW_NAME "maxtouch.fw"
#define MXT_COMMAND_REPORTALL 3
#define THIS_MODULE NULL
#define GFP_KERNEL 0
#define dev_err(dev,...) ((void)(dev))
#define dev_info(dev,...) ((void)(dev))
#define dev_warn(dev,...) ((void)(dev))
static bool irq_enabled, invoke_callback,irq_noautoen;
static unsigned irq_depth,noauto_sets,noauto_clears,early_thread_runs,auto_requests,handshakes;
static int info_error,table_error,irq_error,power_error,input_error,firmware_error,fw_load_error;
static unsigned table_touch,info_reads,boot_probes,boot_sends,acquires,disables,frees,nowaits,powers,inputs,cfg_updates,fw_loads,releases,program_boundaries;
static int probe_fail,range_error; static unsigned mem_frees,irq_frees,irq_requests,resets,input_frees,reg_disables;
static bool probing;
static struct mxt_platform_data pdata; static struct regulator regulator; static struct gpio_desc gpio;
static bool of_device_is_compatible(const struct device_node *n,const char *name) {
 return n && n->wingray && !strcmp(name,"motorola,wingray-maxtouch");
}
static void *dev_get_drvdata(struct device *d) { return d->driver_data; }
static struct device *kobj_to_dev(struct kobject *k) { return k->dev; }
static int mxt_get_info(struct mxt_data *d) { (void)d; ++info_reads; return info_error; }
static int mxt_probe_bootloader(struct mxt_data *d,bool alt) { (void)d;(void)alt;++boot_probes; return 0; }
static int mxt_send_bootloader_cmd(struct mxt_data *d,bool unlock) { (void)d;(void)unlock;++boot_sends;return 0; }
static void msleep(unsigned n) { if(probing && (n==10||n==100)) assert(!irq_enabled); }
static int mxt_get_object_table(struct mxt_data *d) { d->multitouch=table_touch;return table_error; }
static int mxt_acquire_irq(struct mxt_data *d) { (void)d;++acquires;assert(irq_depth==1);--irq_depth;irq_enabled=true;return irq_error; }
static void disable_irq(unsigned irq) { (void)irq;++disables;++irq_depth;irq_enabled=false; }
static void irq_set_status_flags(unsigned irq,unsigned flags) { (void)irq;assert(flags==IRQ_NOAUTOEN);++noauto_sets;irq_noautoen=true; }
static void irq_clear_status_flags(unsigned irq,unsigned flags) { (void)irq;assert(flags==IRQ_NOAUTOEN);++noauto_clears;irq_noautoen=false; }
static int mxt_read_t9_resolution(struct mxt_data *d) { (void)d;return range_error; }
static int mxt_read_t100_config(struct mxt_data *d) { (void)d;return 0; }
static const struct mxt_platform_data *mxt_get_platform_data(struct i2c_client *c) { (void)c;return &pdata; }
static void *kzalloc(size_t n,int f) { (void)f;return calloc(1,n); }
static void kfree(void *p) { ++mem_frees;free(p); }
static void i2c_set_clientdata(struct i2c_client *c,void *d) { c->dev.driver_data=d; }
static void init_completion(int *p) { *p=0; }
static void reinit_completion(int *p) { *p=0; }
static struct regulator *devm_regulator_get(struct device *d,const char *n) { (void)d;(void)n;return probe_fail==1?ERR_PTR(-517):&regulator; }
static int regulator_enable(struct regulator *r) { (void)r;return probe_fail==2?-EIO:0; }
static void regulator_disable(void *r) { (void)r;++reg_disables; }
static int devm_add_action(struct device *d,void (*fn)(void *),void *p) { (void)d;(void)fn;(void)p;return probe_fail==3?-ENOMEM:0; }
static struct gpio_desc *devm_gpiod_get_optional(struct device *d,const char *name,int f) { (void)d;(void)f;return ((probe_fail==4&&!strcmp(name,"enable"))||(probe_fail==5&&!strcmp(name,"reset")))?ERR_PTR(-517):&gpio; }
static void mxt_interrupt(void) {}
static void mxt_suspend_work_handler(void) {}
static int request_threaded_irq(unsigned irq,void *primary,void (*fn)(void),unsigned flags,const char *name,void *data) {
 (void)irq;(void)primary;(void)fn;(void)flags;(void)name;
 ++irq_requests;if(probe_fail==6)return -EBUSY;
 /* Model __setup_irq: it starts the chip before returning unless NOAUTOEN. */
 irq_depth=irq_noautoen?1:0;irq_enabled=!irq_noautoen;
 if(irq_enabled) {
  ++auto_requests;
  struct mxt_data *d=data;
  if(of_device_is_compatible(d->client->dev.of_node,"motorola,wingray-maxtouch")) {
   /* A low CHG preempts probe right here, before its next statement. */
   ++early_thread_runs;
   assert(!"Wingray IRQ thread ran before object setup");
  }
 }
 return 0;
}
static void free_irq(unsigned irq,void *d) { (void)irq;(void)d;++irq_frees;irq_enabled=false; }
static void gpiod_set_value(struct gpio_desc *g,int v) { (void)g;if(probing)assert(v==0?(!irq_enabled&&irq_depth==1):(irq_enabled&&irq_depth==0));++resets; }
static int mxt_wait_for_completion(struct mxt_data *d,int *c,int t) { (void)c;(void)t;assert(d->in_bootloader&&irq_enabled&&!irq_depth);++handshakes;return 0; }
static int mxt_attr_group;
static int sysfs_create_group(struct kobject *k,const void *a) { (void)k;(void)a;return probe_fail==7?-ENOMEM:0; }
static void mxt_free_input_device(struct mxt_data *d) { (void)d;assert(!irq_enabled);++input_frees; }
static void mxt_free_object_table(struct mxt_data *d) {
 if(of_device_is_compatible(d->client->dev.of_node,"motorola,wingray-maxtouch")) assert(!irq_enabled);
 ++frees;
}
static int mxt_init_t7_power_cfg(struct mxt_data *d) { (void)d;++powers;return power_error; }
static int mxt_initialize_input_device(struct mxt_data *d) { (void)d;++inputs;return input_error; }
static int mxt_update_cfg(struct mxt_data *d,const struct firmware *fw) { (void)d;(void)fw;++cfg_updates;return 0; }
static void release_firmware(const struct firmware *f) { (void)f;++releases; }
static int request_firmware_nowait(void *module,bool uevent,const char *name,struct device *dev,int flags,void *ctx,void (*cb)(const struct firmware *,void *)) {
 (void)module;(void)uevent;(void)name;(void)dev;(void)flags; ++nowaits;
 if(invoke_callback && !firmware_error) { static struct firmware f={"test",4};cb(&f,ctx); }
 return firmware_error;
}
static int mxt_load_fw(struct device *dev,const char *name) { (void)dev;(void)name; ++fw_loads;return fw_load_error; }
static int request_firmware(const struct firmware **fw,const char *name,struct device *dev) { (void)fw;(void)name;(void)dev;++program_boundaries;return -ENOSYS; }
static void mxt_update_crc(struct mxt_data *d,unsigned cmd,unsigned value) { (void)d;(void)cmd;(void)value;++program_boundaries; }
static void reset(void) {
 irq_enabled=false; invoke_callback=false;probing=false;irq_depth=1;irq_noautoen=false;
 noauto_sets=noauto_clears=early_thread_runs=auto_requests=handshakes=0;
 probe_fail=range_error=0;mem_frees=irq_frees=irq_requests=resets=input_frees=reg_disables=0;
 info_error=table_error=irq_error=power_error=input_error=firmware_error=fw_load_error=0;
 table_touch=MXT_TOUCH_MULTI_T9;
 info_reads=boot_probes=boot_sends=acquires=disables=frees=nowaits=powers=inputs=cfg_updates=fw_loads=releases=program_boundaries=0;
}
'''
actual = extract('static int mxt_configure_objects(struct mxt_data *data,\n\t\t\t\t const struct firmware *cfg)\n{')
actual += extract('static void mxt_config_cb(')
actual += extract('static int mxt_initialize(')
# Patch 0057 adds one shared policy predicate and attribute visibility callback.
policy = 'static bool mxt_is_wingray(' in s
if policy:
    actual = extract('static bool mxt_is_wingray(') + actual
    actual += extract('static umode_t mxt_attr_is_visible(')
actual += extract('static ssize_t mxt_update_fw_store(')
if policy:
    actual += extract('static void mxt_disable_panel_supply(')
    actual += extract('static int mxt_probe(')
    ranges = extract('static int mxt_initialize_input_device(')
    ranges = ranges[:ranges.index('\tinput_dev = input_allocate_device();')] + '\t(void)num_mt_slots;\n\treturn 0;\n}\n'
    actual += ranges.replace('static int mxt_initialize_input_device(', 'static int guarded_input_ranges(', 1)
if policy:
    # Compile each actual entry prefix through the first external operation.
    cfg = extract('static int mxt_update_cfg(')
    boundary = '\tmxt_update_crc(data, MXT_COMMAND_REPORTALL, 1);'
    cfg = cfg[:cfg.index(boundary) + len(boundary)] + '\n\treturn -ENOSYS;\n}\n'
    actual += cfg.replace('static int mxt_update_cfg(', 'static int guarded_update_cfg(', 1)
    fw = extract('static int mxt_load_fw(')
    boundary = '\tret = request_firmware(&fw, fn, dev);'
    fw = fw[:fw.index(boundary) + len(boundary)] + '\n\treturn ret;\n}\n'
    actual += fw.replace('static int mxt_load_fw(', 'static int guarded_load_fw(', 1)

main = r'''
int main(void) {
 struct device_node node={true}; struct i2c_adapter adapter={0};
 struct i2c_client client={.dev={.of_node=&node},.adapter=&adapter,.addr=0x5b,.irq=17,.name="mxt"};
 struct mxt_data d={.client=&client,.irq=17,.info={0xa0,0,0x10,0xff,30}};
 client.dev.driver_data=&d; client.dev.kobj.dev=&client.dev;
 reset();assert(mxt_initialize(&d)==0);assert(inputs==1&&powers==1&&irq_enabled&&nowaits==0&&cfg_updates==0&&frees==0);
 reset();power_error=-EIO;assert(mxt_initialize(&d)==-EIO);assert(powers==1&&inputs==0&&disables==1&&frees==1&&!irq_enabled);
 reset();input_error=-ENOMEM;assert(mxt_initialize(&d)==-ENOMEM);assert(inputs==1&&disables==1&&frees==1&&!irq_enabled);
 reset();irq_error=-EBUSY;assert(mxt_initialize(&d)==-EBUSY);assert(acquires==1&&disables==1&&frees==1&&powers==0);
 reset();table_touch=0;assert(mxt_initialize(&d)==-EINVAL);assert(acquires==0&&frees==1&&inputs==0);
 reset();table_touch=100;assert(mxt_initialize(&d)==-EINVAL);assert(acquires==0&&frees==1&&inputs==0);
 reset();table_error=-EREMOTEIO;assert(mxt_initialize(&d)==-EREMOTEIO);assert(acquires==0&&frees==0);
 node.wingray=false;
 reset();invoke_callback=true;assert(mxt_initialize(&d)==0);assert(nowaits==1&&cfg_updates==1&&inputs==1&&releases==1);
 reset();table_touch=0;invoke_callback=true;assert(mxt_initialize(&d)==0);assert(nowaits==1&&cfg_updates==1&&inputs==0);
 reset();firmware_error=-ENOENT;assert(mxt_initialize(&d)==-ENOENT);assert(frees==1&&nowaits==1);
 reset();fw_load_error=-EIO;assert(mxt_update_fw_store(&client.dev,NULL,"1",1)==-EIO);assert(fw_loads==1&&nowaits==0);
 reset();assert(mxt_update_fw_store(&client.dev,NULL,"1",1)==1);assert(fw_loads==1&&nowaits==1);
'''
if policy:
    main += r'''
 node.wingray=true;
 reset();range_error=-EREMOTEIO;d.pdata=&pdata;d.multitouch=9;assert(guarded_input_ranges(&d)==-EREMOTEIO);
 node.wingray=false;assert(guarded_input_ranges(&d)==0);node.wingray=true;
 for(int stage=1;stage<=7;++stage) {
  reset();probe_fail=stage;probing=true;
  int error=mxt_probe(&client,NULL);assert(error<0&&mem_frees==1&&client.dev.driver_data==NULL);
  assert(irq_requests==(stage>=6));assert(irq_frees==(stage==7));
  assert(reg_disables==(stage==3));
  assert(!irq_noautoen&&noauto_sets==(stage>=6)&&noauto_clears==(stage>=6)&&early_thread_runs==0);
  if(stage==7)assert(resets==1&&disables==1&&input_frees==1&&frees==1&&irq_depth==1);
 }
 reset();probing=true;assert(mxt_probe(&client,NULL)==0);assert(disables==0&&acquires==1&&resets==1&&irq_enabled&&mem_frees==0&&irq_depth==0&&early_thread_runs==0&&!irq_noautoen&&noauto_sets==1&&noauto_clears==1);
 free(client.dev.driver_data);client.dev.driver_data=&d;
 reset();probing=true;input_error=-ENOMEM;assert(mxt_probe(&client,NULL)==-ENOMEM);assert(disables==1&&frees==1&&irq_frees==1&&mem_frees==1&&client.dev.driver_data==NULL&&irq_depth==1&&!irq_noautoen);
 client.dev.driver_data=&d;
 node.wingray=false;reset();probing=true;invoke_callback=true;
 assert(mxt_probe(&client,NULL)==0);assert(auto_requests==1&&noauto_sets==0&&noauto_clears==0&&handshakes==1&&disables==1&&acquires==1&&irq_depth==0&&irq_enabled);
 free(client.dev.driver_data);client.dev.driver_data=&d;node.wingray=true;
 reset();info_error=-EREMOTEIO;assert(mxt_initialize(&d)==-EREMOTEIO);assert(info_reads==1&&boot_probes==0&&boot_sends==0&&nowaits==0&&acquires==0);
 reset();assert(mxt_update_fw_store(&client.dev,NULL,"1",1)==-EPERM);assert(fw_loads==0&&nowaits==0);
 assert(mxt_attr_is_visible(&client.dev.kobj,&dev_attr_update_fw.attr,0)==0);
 dev_attr_object.attr.mode=0444;assert(mxt_attr_is_visible(&client.dev.kobj,&dev_attr_object.attr,0)==0444);
 static struct firmware cfg={"dummy",5};
 assert(guarded_update_cfg(&d,&cfg)==-EPERM&&program_boundaries==0);
 assert(guarded_load_fw(&client.dev,"ignored")==-EPERM&&program_boundaries==0);
 node.wingray=false;
 assert(guarded_update_cfg(&d,&cfg)==-ENOSYS&&program_boundaries==1);
 assert(guarded_load_fw(&client.dev,"ignored")==-ENOSYS&&program_boundaries==2);
 dev_attr_update_fw.attr.mode=0200;assert(mxt_attr_is_visible(&client.dev.kobj,&dev_attr_update_fw.attr,0)==0200);
 reset();info_error=-EREMOTEIO;assert(mxt_initialize(&d)==0);assert(boot_probes==2&&boot_sends==1&&d.in_bootloader);
'''
main += r'''
 puts("PASS actual mXT init: factory T9, power/input/IRQ faults, synchronized frees and unchanged generic firmware path; Wingray programming guards fail before first side effect; request-time preemption blocked, IRQ depth balanced, generic reset handshake retained.");
 return 0;
}
'''
# Secondary source audit ties policy tests to the real exported attribute group
# and guards volatile control commands against accidental broad write denial.
assert 'DEVICE_ATTR(object, S_IRUGO, mxt_object_show, NULL)' in s
assert 'DEVICE_ATTR(suspended, S_IRUGO | S_IWUSR' in s
assert not any(token in s for token in ('DEVICE_ATTR(update_cfg', 'bin_attribute', 'DEVICE_ATTR(mem_access', 'DEVICE_ATTR(debug'))
start = extract('static void mxt_start(struct mxt_data *data)\n{')
assert 'mxt_set_t7_power_cfg(data, MXT_POWER_CFG_RUN)' in start
assert 'mxt_t6_command(data, MXT_COMMAND_CALIBRATE, 1, false)' in start
assert 'MXT_COMMAND_BACKUPNV' not in start
if policy:
    assert '.is_visible = mxt_attr_is_visible' in s
with tempfile.TemporaryDirectory(prefix='xoom-mxt-policy-') as tmp:
    path = Path(tmp)
    (path/'test.c').write_text(fixture+actual+main)
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable','-Wno-unused-parameter','-fsanitize=undefined','-O2',str(path/'test.c'),'-o',str(path/'test')],check=True)
    subprocess.run([str(path/'test')],check=True)
    vulnerable = actual.replace('irq_set_status_flags(client->irq, IRQ_NOAUTOEN);', '(void)0; /* missing request-time mask */', 1)
    assert vulnerable != actual
    negative_main = r'''
int main(void) {
 struct device_node node={true};struct i2c_adapter adapter={0};
 struct i2c_client client={.dev={.of_node=&node},.adapter=&adapter,.addr=0x5b,.irq=17,.name="mxt"};
 reset();probing=true;return mxt_probe(&client,NULL);
}
'''
    (path/'vulnerable.c').write_text(fixture+vulnerable+negative_main)
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable','-Wno-unused-parameter','-fsanitize=undefined','-O2',str(path/'vulnerable.c'),'-o',str(path/'vulnerable')],check=True)
    failed = subprocess.run([str(path/'vulnerable')],capture_output=True,text=True)
    assert failed.returncode != 0 and 'Wingray IRQ thread ran before object setup' in failed.stderr
    print('PASS negative control: removing NOAUTOEN fails inside request_threaded_irq before caller can mask.')
