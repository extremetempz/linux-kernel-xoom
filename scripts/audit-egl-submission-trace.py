#!/usr/bin/env python3
"""Decode only observed NVIDIA submission framing; never replay GPU commands."""
from pathlib import Path
import argparse, collections, hashlib, json, re, struct

CHANNELS={'/dev/nvhost-gr2d','/dev/nvhost-gr3d'}
FLUSH=0x80044801

def hex_string(text):
    assert re.fullmatch(r'(?:\\x[0-9a-fA-F]{2})*',text), 'Require -xx trace strings'
    return bytes.fromhex(text.replace('\\x',''))

def audit(text):
    assert '<unfinished ...>' not in text and 'resumed>' not in text, 'Split trace calls need explicit reassembly'
    fds={};devices=set();jobs=[];requests=collections.Counter()
    for line in text.splitlines():
        if 'clone(' in line:
            assert 'CLONE_FILES' in line and 'CLONE_THREAD' in line, 'Only shared-FD test threads supported'
        m=re.search(r'open(?:at)?\((?:[^,]+, )?"((?:\\x[0-9a-fA-F]{2})+)".*?\)\s+= (\d+)',line)
        if m:
            name=hex_string(m[1]).decode();fd=int(m[2]);assert fd not in fds
            fds[fd]={'name':name,'remaining':0,'pending':None}
            if name.startswith('/dev/'):devices.add(name)
            continue
        m=re.search(r'dup(?:2)?\((\d+)(?:, \d+)?\)\s+= (\d+)',line)
        if m:
            old,new=map(int,m.groups())
            if old in fds:fds[new]=fds[old]
            continue
        m=re.search(r'write\((\d+), "((?:\\x[0-9a-fA-F]{2})*)"(?:\.\.\.)?, (\d+)\)\s+= (-?\d+)',line)
        if m and int(m[1]) in fds:
            state=fds[int(m[1])]
            if state['name'] not in CHANNELS:continue
            data=hex_string(m[2]);count=int(m[3]);returned=int(m[4]);assert returned==count and returned>0,'Failed/partial channel write'
            if state['remaining']:
                assert count<=state['remaining'], 'Write crosses payload/header boundary'
                state['remaining']-=count
            else:
                assert state['pending'] is None,'Previous job not flushed'
                assert count==len(data)==24,'Observed stream is not a separate six-word header'
                syncpt,incr,cmdbufs,relocs,waits,mask=struct.unpack('<6I',data)
                assert syncpt<32 and 0<incr<100000 and 0<cmdbufs<1024 and relocs<65536 and waits<65536
                state['pending']={'channel':state['name'],'syncpoint':syncpt,'increments':incr,'command_buffers':cmdbufs,'relocations':relocs,'wait_checks':waits,'wait_mask':mask,'header_bytes':24}
                state['remaining']=12*cmdbufs+16*relocs+16*waits
            continue
        m=re.search(r'ioctl\((0x[0-9a-f]+|\d+), (0x[0-9a-f]+), .*\)\s+= (-?\w+)',line)
        if m and int(m[1],0) in fds:
            state=fds[int(m[1],0)];request=int(m[2],16)
            if state['name'].startswith('/dev/nv') or state['name']=='/dev/tegra_sema':requests[(state['name'],hex(request))]+=1
            if state['name'] in CHANNELS and request==FLUSH:
                assert int(m[3],0)==0,'Failed channel flush'
                assert state['remaining']==0 and state['pending'] is not None,'Incomplete/missing submission at flush'
                jobs.append(state['pending']);state['pending']=None
            continue
        if 'ioctl(' in line:
            m=re.search(r'ioctl\((\d+),',line)
            if m and int(m[1]) in fds and fds[int(m[1])]['name'] in CHANNELS:
                raise AssertionError('Use numeric ioctl decoding; symbolic HID names are ambiguous')
        m=re.search(r'close\((\d+)\)\s+= 0',line)
        if m and int(m[1]) in fds:
            state=fds.pop(int(m[1]));assert not state['remaining'] and state['pending'] is None,'Channel closed with incomplete job'
    assert jobs,'No fully framed channel jobs observed'
    assert all(not x['remaining'] and x['pending'] is None for x in fds.values())
    return {'original_kernel_trace_only':True,'linux44_gpu_rendering_proven':False,
            'observed_header_bytes':24,'jobs':jobs,'job_counts':dict(collections.Counter(x['channel'] for x in jobs)),
            'device_paths':sorted(x for x in devices if x in CHANNELS or x in {'/dev/nvmap','/dev/nvhost-ctrl','/dev/tegra_sema'}),
            'ioctl_counts':[{'device':d,'request':r,'count':n} for (d,r),n in sorted(requests.items())]}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists(),'Preserve earlier analysis'
    data=a.trace.read_bytes();result=audit(data.decode());result['trace_sha256']=hashlib.sha256(data).hexdigest()
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Observed successful 24-byte legacy header/flush sequences:',result['job_counts'],'; no Linux 4.4 rendering claim.')
