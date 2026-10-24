#!/usr/bin/env python3
"""Verify donor power-sequence return propagation and clock ownership."""
from pathlib import Path
import re
import subprocess
import tempfile
source=(Path(__file__).resolve().parents[1]/'sources/kernel-donor/drivers/staging/tegra/video/host/nvhost_acm.c').read_text()
def function(name):
    start=re.search(r'^static int '+name+r'\(',source,re.M).start()
    end=source.index('{',start)+1;depth=1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#define dev_info(...) ((void)0)
struct clk{int refs;};
struct nvhost_device{int powergate_ids[2];struct clk *clk[1];void *rst;};
static int powered,error,seq_calls,off_calls,disables;
static int tegra_powergate_is_powered(int id){assert(id==1);return powered;}
static int tegra_powergate_power_off(int id){assert(id==1);off_calls++;return error;}
static int tegra_powergate_sequence_power_up(int id,struct clk*c,void*r){assert(id==1&&r);seq_calls++;if(error)return error;c->refs++;return 0;}
static void clk_disable_unprepare(struct clk*c){assert(c->refs==1);c->refs--;disables++;}
'''
main=r'''
int main(void){
 struct clk clk={0};struct nvhost_device d={{1,-1},{&clk},&d};
 error=-EIO;assert(do_unpowergate_locked(&d)==-EIO);assert(seq_calls==1&&!disables&&!clk.refs);
 error=0;assert(!do_unpowergate_locked(&d));assert(seq_calls==2&&disables==1&&!clk.refs);
 d.rst=NULL;assert(do_unpowergate_locked(&d)==-EINVAL);assert(seq_calls==2);
 powered=1;error=-ETIMEDOUT;assert(do_powergate_locked(&d)==-ETIMEDOUT);assert(off_calls==1&&disables==1);
 error=0;assert(!do_powergate_locked(&d));assert(off_calls==2&&disables==1);
 d.powergate_ids[0]=-1;assert(!do_powergate_locked(&d));assert(!do_unpowergate_locked(&d));
 assert(seq_calls==2&&off_calls==2&&disables==1);
 puts("PASS actual power sequence: failure propagation, missing reset, success balance and no duplicate clock disable (UBSan)");
}
'''
with tempfile.TemporaryDirectory() as t:
    p=Path(t)/'test.c';p.write_text(prefix+function('do_powergate_locked')+function('do_unpowergate_locked')+main)
    subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True)
    subprocess.run([t+'/test'],check=True)
