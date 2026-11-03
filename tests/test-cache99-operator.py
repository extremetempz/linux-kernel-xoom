#!/usr/bin/env python3
"""Reply sequencing tests; no serial device operations."""
from pathlib import Path
import importlib.util,io,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
spec=importlib.util.spec_from_file_location('operator99',R/'scripts/cache99-operator.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Fake(m.Link):
 def __init__(self,chunks):self.buffer=b'';self.chunks=list(chunks);self.sent=[]
 def send(self,line):self.sent.append(line)
 def read(self,deadline):
  if not self.chunks:raise TimeoutError('no verified reply')
  b=self.chunks.pop(0);self.buffer+=b;return b
nonce='ab'*16
f=Fake([b'CACHE99_PREFLIGHT_PASSED_',b'P9_RO_ALL_OTHERS_RO\n']);m.preflight(f,nonce)
assert f.sent==['PREFLIGHT_P9 '+nonce]
for chunks in ([b'CACHE99_PREFLIGHT_FAILED_original_hash\n'],[b'irrelevant response\n']):
 f=Fake(chunks)
 try:m.preflight(f,nonce)
 except (RuntimeError,TimeoutError):pass
 else:raise AssertionError('unverified preflight accepted')
 assert not any(s.startswith('REPAIR') for s in f.sent)
f=Fake([b'CACHE99_ARMED '+b'cd'*16+b'\n'])
try:f.wait(('CACHE99_ARMED '+nonce).encode(),1)
except TimeoutError:pass
else:raise AssertionError('wrong arm nonce accepted')
print('PASS: split replies accepted, failed/missing preflight and wrong nonce block progression')
