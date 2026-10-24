#!/usr/bin/env python3
"""Fault-test actual PMC reset/clock/power rollback sequence."""
from pathlib import Path
import tempfile,subprocess
s=(Path(__file__).resolve().parents[1]/'sources/kernel-donor/drivers/soc/tegra/pmc.c').read_text();a=s.index('int tegra_powergate_sequence_power_up(');e=s.index('{',a)+1;d=1
while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
struct clk{int on;};struct reset_control{int asserted;};static int fault,step,powered,logs,rollback_fault;
#define pr_err(...) (logs++)
static int reset_control_assert(struct reset_control*r){if(++step==fault)return -EIO;if(rollback_fault&&step>5)return -EFAULT;r->asserted=1;return 0;}
static int tegra_powergate_power_on(int id){assert(id==1);if(++step==fault)return -ENOSPC;powered=1;return 0;}
static int clk_prepare_enable(struct clk*c){assert(powered);if(++step==fault)return -ENOMEM;c->on=1;return 0;}
static void usleep_range(int a,int b){assert(a==10&&b==20);}
static int tegra_powergate_remove_clamping(int id){assert(id==1&&powered);return ++step==fault?-EAGAIN:0;}
static int reset_control_deassert(struct reset_control*r){assert(powered&&r->asserted);if(++step==fault)return -ETIMEDOUT;r->asserted=0;return 0;}
static void clk_disable_unprepare(struct clk*c){assert(c->on);c->on=0;}
static int tegra_powergate_power_off(int id){assert(id==1&&powered);if(rollback_fault)return -EFAULT;powered=0;return 0;}
'''
main=r'''
int main(void){int errors[]={0,-EIO,-ENOSPC,-ENOMEM,-EAGAIN,-ETIMEDOUT};struct clk c;struct reset_control r;
 for(fault=1;fault<=5;fault++){c=(struct clk){0};r=(struct reset_control){0};step=powered=logs=0;assert(tegra_powergate_sequence_power_up(1,&c,&r)==errors[fault]);assert(!c.on&&!powered&&!logs);}
 fault=0;step=0;assert(!tegra_powergate_sequence_power_up(1,&c,&r));assert(c.on&&powered&&!r.asserted);
 fault=5;step=powered=logs=0;c.on=0;rollback_fault=1;assert(tegra_powergate_sequence_power_up(1,&c,&r)==-ETIMEDOUT);assert(!c.on&&logs==2);
 puts("PASS actual PMC: reset/power/clock/clamp/deassert failures, balanced successful rollback and original error retained on rollback faults (UBSan)");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+s[a:e]+main);subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
