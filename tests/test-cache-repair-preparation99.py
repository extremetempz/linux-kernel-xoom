#!/usr/bin/env python3
"""Host regular-file identity gate; no devices or privileged operations."""
import importlib.util,struct,tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('prep',ROOT/'scripts/prepare-cache-repair99.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'copy.img';n=2*1024*1024;b=bytearray(n)
 struct.pack_into('<I',b,1028,1024);struct.pack_into('<I',b,1048,0)
 struct.pack_into('<HHH',b,1080,0xef53,1,1)
 struct.pack_into('<III',b,1116,28,66,19)
 p.write_bytes(b);m.SIZE=n;m.REPAIRED=m.digest(p)
 assert m.check_copy(p)['reasons']==[]
 alias=p.parent/'alias';alias.symlink_to(p)
 for bad in (alias,p.parent):
  try:m.check_copy(bad)
  except ValueError:pass
  else:raise AssertionError('nonregular accepted')
 b[1120]|=4;p.write_bytes(b);m.REPAIRED=m.digest(p)
 try:m.check_copy(p)
 except ValueError:pass
 else:raise AssertionError('journal recovery accepted')
 b[1120]&=~4;p.write_bytes(b);m.REPAIRED='0'*64
 try:m.check_copy(p)
 except ValueError:pass
 else:raise AssertionError('wrong hash accepted')
print('PASS: host copy regular-file/hash/healthy-feature checks; no tablet access')
