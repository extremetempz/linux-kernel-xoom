#!/usr/bin/env python3
"""Execute the actual rfkill callback against fault-injected regulator/GPIOs."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1]
s=(r/'sources/kernel-donor/net/rfkill/rfkill-wingray-bt.c').read_text()
body=s[s.index('static int wingray_bt_set_block'):s.index('static const struct rfkill_ops')]
preamble='''#include <assert.h>
#include <stdbool.h>
struct gpio_desc {int value;};
struct regulator {int refs, enable_error, disable_error, enables, disables;};
struct wingray_bt {struct gpio_desc *reset,*shutdown,*wake,*host_wake;struct regulator *vdd;bool rail_enabled;};
static int regulator_enable(struct regulator *r){r->enables++;if(r->enable_error)return r->enable_error;r->refs++;return 0;}
static int regulator_disable(struct regulator *r){r->disables++;if(r->disable_error)return r->disable_error;r->refs--;return 0;}
static void gpiod_set_value_cansleep(struct gpio_desc *p,int v){p->value=v;}
'''
test='''int main(void){
struct gpio_desc reset={0},shutdown={0},wake={0};
struct regulator rail={.refs=1}; /* Wi-Fi already holds one independent vote. */
struct wingray_bt bt={.reset=&reset,.shutdown=&shutdown,.wake=&wake,.vdd=&rail};
assert(!wingray_bt_set_block(&bt,true)); assert(rail.disables==0);
rail.enable_error=-5;assert(wingray_bt_set_block(&bt,false)==-5);
assert(!bt.rail_enabled&&!reset.value&&!wake.value&&rail.refs==1);
rail.enable_error=0;assert(!wingray_bt_set_block(&bt,false));
assert(bt.rail_enabled&&reset.value&&wake.value&&!shutdown.value&&rail.refs==2);
int calls=rail.enables;assert(!wingray_bt_set_block(&bt,false));assert(rail.enables==calls);
rail.disable_error=-5;assert(wingray_bt_set_block(&bt,true)==-5);
assert(bt.rail_enabled&&!reset.value&&!wake.value&&!shutdown.value&&rail.refs==2);
assert(!wingray_bt_set_block(&bt,false));assert(reset.value&&wake.value&&rail.refs==2);
rail.disable_error=0;assert(!wingray_bt_set_block(&bt,true));assert(!bt.rail_enabled&&rail.refs==1);
assert(!wingray_bt_set_block(&bt,true));assert(rail.refs==1);
return 0;}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(preamble+body+test)
 subprocess.run(['cc','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS actual Bluetooth power callback: shared Wi-Fi vote, idempotence, enable/disable faults')
