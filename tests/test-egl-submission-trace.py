#!/usr/bin/env python3
"""Exercise trace framing with synthetic data; no command replay or GPU access."""
from pathlib import Path
import importlib.util,struct
p=Path(__file__).resolve().parents[1]/'scripts/audit-egl-submission-trace.py'
spec=importlib.util.spec_from_file_location('audit',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def quoted(data):return ''.join('\\x%02x'%b for b in data)
def open_(fd=3,name='/dev/nvhost-gr3d'):return f'123 open("{quoted(name.encode())}", O_RDWR) = {fd}\n'
def write(data,fd=3):return f'123 write({fd}, "{quoted(data)}", {len(data)}) = {len(data)}\n'
def flush(fd=3):return f'123 ioctl({hex(fd)}, 0x80044801, 0x1234) = 0\n'
header=struct.pack('<6I',22,1,2,0,0,0)
trace=open_()+write(header)+write(bytes(24))+flush()+'123 close(3) = 0\n'
r=m.audit(trace);assert r['job_counts']=={'/dev/nvhost-gr3d':1} and r['jobs'][0]['command_buffers']==2
# A 24-byte payload must not be misclassified as another header.
assert len(r['jobs'])==1
r=m.audit(open_()+ '123 dup(3) = 4\n'+write(header,4)+write(bytes(24),4)+flush(4)+'123 close(4) = 0\n123 close(3) = 0\n');assert len(r['jobs'])==1
bad=[open_()+write(header[:16])+flush(),open_()+write(header)+flush(),open_()+write(header)+write(bytes(24))+flush().replace('= 0','= -1'),open_()+write(header)+write(bytes(24))+'123 ioctl(3, HIDIOCGVERSION, 0x1234) = 0\n',trace+'123 clone(flags=CLONE_VM) = 124\n',trace+'123 write(3, <unfinished ...>\n',open_()+write(header)+write(bytes(24))+'123 close(3) = 0\n']
for t in bad:
 try:m.audit(t)
 except (AssertionError,ValueError):pass
 else:raise AssertionError('Invalid trace accepted')
try:m.audit(open_(name='/dev/log/main')+write(header)+write(bytes(24))+flush())
except AssertionError:pass
else:raise AssertionError('Unrelated fd was counted as NVIDIA job')
print('PASS trace framing: payload/header distinction, duplicate fd, short/incomplete/failed streams, ambiguous labels and unrelated devices')
