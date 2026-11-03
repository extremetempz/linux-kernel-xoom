#!/usr/bin/env python3
"""Prepare RAM-only gated p9 repair runtime. Never contacts or flashes a device."""
from pathlib import Path
import argparse,hashlib,lzma,stat,subprocess,json,struct
from android44_image import Entry,parse_newc,pack_newc,BUSYBOX_SHA256
ROOT=Path(__file__).resolve().parents[1]
CHECKER='b063d57f8bdd3c8474a6ad3ad69faa13dfac3e17d251da50557052b07096d171'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--validation-archive',type=Path,required=True)
 p.add_argument('--cache-fixture',type=Path,required=True)
 p.add_argument('--busybox',type=Path,required=True)
 p.add_argument('--build-root',type=Path,required=True)
 p.add_argument('--output-dir',type=Path,required=True)
 a=p.parse_args();out=a.output_dir
 if out.exists():p.error('new output directory required')
 raw=a.validation_archive.read_bytes();old=parse_newc(lzma.decompress(raw))
 bb=a.busybox.read_bytes();assert sha(bb)==BUSYBOX_SHA256
 chunks={n:e for n,e in old.items() if n.startswith(('chunks/','fixtures/'))}
 checker=b''.join(chunks[n].data for n in sorted(chunks) if n.startswith('chunks/e2fsck.'))
 assert sha(checker)==CHECKER
 manifest=chunks['chunks/manifest'].data.decode().splitlines()
 assert manifest[-1]==f'FINAL {CHECKER} {len(checker)}'
 for line in manifest[:-1]:
  name,h,size=line.split();data=chunks['chunks/'+name].data
  assert sha(data)==h and len(data)==int(size)
 out.mkdir(mode=0o700)
 entries={n:Entry(n,stat.S_IFDIR|0o755) for n in ('bin','chunks','fixtures','dev','proc','sys','tmp','run','dev/pts')}
 entries.update(chunks)
 fixture=a.cache_fixture.read_bytes();plain=lzma.decompress(fixture);assert len(plain)==16*1024*1024
 entries['fixtures/journal-padding.img.xz']=Entry('fixtures/journal-padding.img.xz',stat.S_IFREG|0o644,fixture)
 entries['bin/busybox']=Entry('bin/busybox',stat.S_IFREG|0o755,bb)
 names={'bin/usb-report-loop':'usb-report-loop.sh','bin/diagnostic-report':'cache99-report.sh',
 'bin/diagnostic-server':'cache99-server.sh','bin/cache99-preflight':'cache99-preflight.sh',
 'bin/cache99-repair':'cache99-repair.sh','bin/offline97-ramtest':'cache99-ramtest.sh'}
 for dest,src in names.items():entries[dest]=Entry(dest,stat.S_IFREG|0o755,(ROOT/'diagnostic'/src).read_bytes())
 init=(ROOT/'diagnostic/offline97-init.sh').read_bytes().replace(b'#__CHUNK_MANIFEST__\n',chunks['chunks/manifest'].data)
 entries['init']=Entry('init',stat.S_IFREG|0o755,init)
 gcc=a.build_root/'toolchain/bin/arm-linux-androideabi-gcc'
 helper_hashes={}
 for mode in ('release','lock'):
  binary=out/('cache99-'+mode)
  args=[str(gcc),'-std=gnu11','-nostdlib','-static','-marm','-march=armv7-a','-mfloat-abi=softfp','-mfpu=vfpv3-d16','-fomit-frame-pointer','-fno-stack-protector','-fno-builtin','-fno-pic','-Wall','-Wextra','-Werror','-O2','-Wl,-e,_start','-Wl,--build-id=none','-isystem',str(a.build_root/'headers/include')]
  if mode=='lock':args.append('-DCACHE_LOCK_ONLY')
  subprocess.run(args+[str(ROOT/'diagnostic/cache99-policy.c'),'-o',str(binary)],check=True)
  b=binary.read_bytes();assert b[:7]==b'\x7fELF\x01\x01\x01' and b[18:20]==b'\x28\0'
  assert not subprocess.check_output(['nm','-u',str(binary)],text=True).strip()
  assert 'INTERP' not in subprocess.check_output(['readelf','-lW',str(binary)],text=True)
  entries['bin/cache99-'+mode]=Entry('bin/cache99-'+mode,stat.S_IFREG|0o755,b)
  helper_hashes[mode]=sha(b)
 archive=pack_newc(entries);(out/'runtime.cpio').write_bytes(archive)
 (out/'manifest.json').write_text(json.dumps({'runtime_sha256':sha(archive),'checker_sha256':CHECKER,
 'helpers':helper_hashes,'physical_repair_automatic':False,'hardware_validated':False,
 'sources':{str((ROOT/'diagnostic'/n).relative_to(ROOT)):sha((ROOT/'diagnostic'/n).read_bytes()) for n in [*names.values(),'offline97-init.sh','cache99-policy.c']}},indent=2)+'\n')
 print('RAM-only runtime prepared, not flashed:',out)
if __name__=='__main__':main()
