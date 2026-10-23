#!/usr/bin/env python3
"""Decode a local 128-byte Wingray SMP snapshot; never contacts hardware."""
import argparse,json,struct
from pathlib import Path

def decode(raw,cookie):
    if len(raw)!=128: raise ValueError('Require exactly 128 bytes')
    w=struct.unpack('<32I',raw)
    if w[:3]!=(0x58534d50,1,cookie): raise ValueError('Magic/version/build cookie mismatch; refuse stale or unrelated record')
    allowed={0,1,2,4,5,6,7,8,9,10}
    if any(value for i,value in enumerate(w) if i not in allowed): raise ValueError('Unexpected reserved data')
    cpu0={0:'not recorded',1:'mapping initialized',2:'before reset-handler install',3:'reset-handler installed',4:'before SCU setup',5:'after SCU setup',6:'before platform secondary request',10:'before CPU reset assertion',11:'reset assertion returned',12:'flow halt clear returned',13:'CPU clock enable returned',14:'before reset release',15:'reset release returned',16:'platform secondary request returned',17:'online wait/result recorded'}
    cpu1={0:'not recorded',1:'secondary C after MM switch',2:'before CPU-starting notifications',3:'CPU-starting notifications returned',4:'delay calibration returned',5:'online completion signalled'}
    if w[4] not in cpu0 or w[5] not in (0,1) or w[6] not in cpu1 or w[10] not in (0,1): raise ValueError('Unknown checkpoint value')
    result=struct.unpack('<i',struct.pack('<I',w[9]))[0] if w[4]==17 else None
    return {'cookie':hex(cookie),'cpu0_last_checkpoint':cpu0[w[4]],'cpu1_reset_entry_recorded':bool(w[5]),'cpu1_last_checkpoint':cpu1[w[6]],'secondary_entry_physical':hex(w[7]),'reset_vector_readback':hex(w[8]),'cpu_up_result':result,'cpu1_online_observed_by_cpu0':bool(w[10]) if w[4]==17 else None,'limit':'Checkpoints show reached locations, not the cause of a stop. Build cookie is not a unique boot nonce; preflight and attempt provenance remain required.'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot',type=Path);p.add_argument('--cookie',type=lambda x:int(x,0),required=True);a=p.parse_args();print(json.dumps(decode(a.snapshot.read_bytes(),a.cookie),indent=2))
