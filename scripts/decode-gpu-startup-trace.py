#!/usr/bin/env python3
"""Decode the bounded cookie-49 startup record; never contacts hardware."""
from pathlib import Path
import argparse, hashlib, json, struct
COOKIE = 0x584d0049
FIELDS = {'cpu0':0x10,'cpu1_reset':0x14,'cpu1_c':0x18,'secondary_entry':0x1c,
          'reset_vector':0x20,'cpu1_result':0x24,'cpu1_online':0x28,
          'initcall_function':0x2c,'initcall_result':0x30,'initcall_state':0x34,
          'host_stage':0x38,'host_result':0x3c,'gr2d_stage':0x40,'gr2d_result':0x44,
          'gr3d_stage':0x48,'gr3d_result':0x4c,'kernel_stage':0x50,'exec_result':0x54,
          'reporter_stage':0x58,'userspace_stage':0x5c,'usb_stage':0x60,'usb_result':0x64,'panic_seen':0x68}
def signed(n):
    return n-(1<<32) if n & (1<<31) else n

def decode(data, system_map, cookie=COOKIE):
    assert cookie in (COOKIE,0x584d0050,0x584d0051,0x584d0052,0x584d0053,0x584d0054,0x584d0055,0x584d0056,0x584d0057,0x584d0059,0x584d0060)
    assert len(data)==128, 'Require exactly one complete 128-byte snapshot'
    w=struct.unpack('<32I',data)
    assert w[:3]==(0x58534d50,1,cookie), 'Wrong/stale magic, version or build cookie'
    assert w[3]==0, 'Reserved header word changed'
    if cookie==COOKIE:
        assert not any(w[0x6c//4:]), 'Reserved trace words changed'
    result={n: signed(w[o//4]) if n.endswith('_result') else w[o//4] for n,o in FIELDS.items()}
    assert result['initcall_state'] in (0,1,2)
    assert result['kernel_stage']<=8 and result['reporter_stage']<=3
    assert result['userspace_stage']<=5 and result['panic_seen']<=1
    names=[]
    if result['initcall_state']:
        address=result['initcall_function']
        for line in system_map.splitlines():
            cells=line.split()
            if len(cells)==3 and cells[1] in ('t','T') and int(cells[0],16)==address:
                names.append(cells[2])
        assert names, 'Initcall address does not match the supplied kernel System.map'
    result.update(initcall_symbols=names,trace_cookie=hex(cookie),
                  trace_sha256=hashlib.sha256(data).hexdigest(),
                  system_map_sha256=hashlib.sha256(system_map.encode()).hexdigest(),
                  limits='A checkpoint records progress, not causation. Missing/stale records cannot locate a failure. Reset retention and instrumentation timing can affect results. No GPU rendering is enabled.')
    if cookie==0x584d0057:
        result['usb_reply_checkpoint'] = {0:'not recorded',1:'USB initialization checkpoint',
            2:'USB initialization checkpoint',3:'before readiness printf',
            4:'readiness printf returned success',5:'readiness printf returned failure'}.get(
                result['usb_stage'], 'unrecognized USB stage')
        result['usb_reply_limit'] = 'Local write success does not prove USB queue/completion or host receipt. Missing return checkpoint can also mean process exit/reset.'
    if cookie in (0x584d0056,0x584d0057,0x584d0059,0x584d0060):
        for engine in ('gr2d','gr3d'):
            stage=result[engine+'_stage']
            if 0x500<=stage<0x600:
                result[engine+'_runtime']={'operation':'ioctl entry','number':stage-0x500}
            elif 0x600<=stage<0x700:
                result[engine+'_runtime']={'operation':'ioctl returned','number':stage-0x600}
            else:
                names={0x400:'channel open entry',0x401:'channel acquired',0x402:'before context allocation',0x403:'open returned',0x4ff:'open failed',0x410:'channel write entry',0x411:'submit header processed',0x412:'write returned',0x41f:'write failed',0x420:'before job pin',0x421:'job pin returned',0x422:'before channel submit',0x423:'channel submit returned'}
                if stage in names:result[engine+'_runtime']={'operation':names[stage]}
    if cookie in (0x584d0055,0x584d0056,0x584d0057,0x584d0059,0x584d0060):
        result['limits']=result['limits'].replace('No GPU rendering is enabled.','A bounded userspace rendering probe is enabled; checkpoints alone do not prove GPU rendering.')
    if cookie in (0x584d0059,0x584d0060):
        result['limits']='Accelerated Android candidate: checkpoints record progress, not rendering, display or boot-completion proof. Reset retention and timing can affect results.'
    if cookie in (0x584d0050,0x584d0051,0x584d0052,0x584d0053,0x584d0054,0x584d0055,0x584d0056,0x584d0057,0x584d0059,0x584d0060):
        result['panic_prefix']=data[0x6c:0x80].split(b'\0',1)[0].decode('utf-8',errors='replace')
        if cookie in (0x584d0052,0x584d0053,0x584d0054,0x584d0055,0x584d0056,0x584d0057,0x584d0059,0x584d0060) and result['panic_seen']:
            import re
            pair=re.fullmatch(r'RD ([0-9a-f]{8}) ([0-9a-f]{8})',result['panic_prefix'])
            if pair:
                result['initrd_fnv1a32']=pair[1]
                result['initrd_size']=int(pair[2],16)

    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot',type=Path);p.add_argument('--kernel-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    from gpu_test import validate_artifacts, startup_cookie
    cookie=startup_cookie(a.kernel_dir)
    validate_artifacts(a.kernel_dir,startup_trace=True,trace_cookie=cookie)
    assert not a.output.exists(), 'Preserve previous evidence'
    result=decode(a.snapshot.read_bytes(),(a.kernel_dir/'System.map').read_text(),cookie=cookie)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
