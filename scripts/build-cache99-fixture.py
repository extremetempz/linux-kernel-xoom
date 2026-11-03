#!/usr/bin/env python3
"""Create a synthetic RAM-fixture source, never using real filesystem contents."""
from pathlib import Path
import argparse,hashlib,json,lzma,os,struct,subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
if a.output_dir.exists():p.error('new directory required')
a.output_dir.mkdir();image=a.output_dir/'journal-padding.img'
with image.open('xb') as f:f.truncate(16*1024*1024)
args=['mke2fs','-t','ext4','-F','-b','4096','-I','256','-N','4096','-U','11111111-2222-3333-4444-555555555555','-O','has_journal,ext_attr,resize_inode,filetype,extent,sparse_super,large_file,uninit_bg,^64bit,^metadata_csum,^dir_nlink,^extra_isize','-E','lazy_itable_init=0,lazy_journal_init=0,nodiscard',str(image)]
r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True);(a.output_dir/'mke2fs.log').write_bytes(r.stdout)
with image.open('r+b') as f:
 f.seek(1024);sb=f.read(1024);assert struct.unpack_from('<I',sb,40)[0]==4096
 incompat=struct.unpack_from('<I',sb,96)[0];f.seek(1120);f.write(struct.pack('<I',incompat|4))
 f.seek(4096+4);bitmap=struct.unpack('<I',f.read(4))[0]
 f.seek(bitmap*4096+4095);assert f.read(1)==b'\xff';f.seek(-1,1);f.write(b'\0');f.flush();os.fsync(f.fileno())
b=image.read_bytes();(a.output_dir/'journal-padding.img.xz').write_bytes(lzma.compress(b))
(a.output_dir/'manifest.json').write_text(json.dumps({'size':len(b),'sha256':hashlib.sha256(b).hexdigest(),'synthetic':True,'argv':args},indent=2)+'\n')
print('Created synthetic journal/padding fixture:',a.output_dir)
