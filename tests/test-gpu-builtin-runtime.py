#!/usr/bin/env python3
"""Verify the intended RAM filesystem is actually linked into the tested kernel."""
from pathlib import Path
import argparse,gzip,struct
r=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--attempt',type=int,choices=(54,55,56),default=56);a=p.parse_args()
k=r/('artifacts/gpu-startup54-kernel' if a.attempt==54 else f'artifacts/gpu-render{a.attempt}-kernel');out=a.build/'out'
symbols={v[2]:int(v[0],16) for line in (k/'System.map').read_text().splitlines() if len(v:=line.split())==3}
elf=(out/'vmlinux').read_bytes();assert elf[:7]==b'\x7fELF\x01\x01\x01'
shoff=struct.unpack_from('<I',elf,32)[0];entsize,n=struct.unpack_from('<HH',elf,46)
sections=[struct.unpack_from('<10I',elf,shoff+i*entsize) for i in range(n)]
def linked(address,size):
 for s in sections:
  if s[1]==1 and s[3]<=address and address+size<=s[3]+s[5]:
   pos=s[4]+address-s[3];return elf[pos:pos+size]
 raise AssertionError('Linked bytes not present in ELF sections')
builtin=(k/'builtin-initramfs.cpio.gz').read_bytes()
assert linked(symbols['__initramfs_start'],len(builtin))==builtin
assert struct.unpack('<I',linked(symbols['__initramfs_size'],4))[0]==len(builtin)
reference=gzip.decompress((r/'artifacts/gpu-startup53-ready/ramdisk.cpio.gz').read_bytes()) if a.attempt==54 else (k/'runtime-source.cpio').read_bytes()
assert gzip.decompress(builtin)==reference
piggy=(out/'arch/arm/boot/compressed/piggy.gzip').read_bytes();z=(k/'zImage').read_bytes()
assert z.count(piggy)==1 and gzip.decompress(piggy)==(out/'arch/arm/boot/Image').read_bytes()
assert symbols['_end']-symbols['_text']+len(z)+0x20000<0x1000000
print('PASS built-in runtime exact ELF bytes/size, intended cpio, zImage compressed Image and conservative 16MiB footprint bound')
