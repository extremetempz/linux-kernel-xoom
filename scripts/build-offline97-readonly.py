#!/usr/bin/env python3
"""Build a read-only offline97 RAM-validation boot image. Never touches a device."""
import argparse, hashlib, json, lzma, stat
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from android44_image import Entry, parse_newc, pack_newc, boot_image
ROOT=Path(__file__).resolve().parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--inspect-image',type=Path,required=True)
 ap.add_argument('--runtime-source',type=Path,required=True)
 ap.add_argument('--checker',type=Path,required=True)
 ap.add_argument('--fixtures',type=Path,required=True)
 ap.add_argument('--output-dir',type=Path,required=True)
 ap.add_argument('--uncompressed',action='store_true')
 a=ap.parse_args()
 if a.output_dir.exists(): ap.error('use a new output directory')
 image=a.inspect_image.read_bytes()
 if image[:8]!=b'ANDROID!': raise SystemExit('not an Android boot image')
 ks,ka,rs,ra,ss,_,tags,page=__import__('struct').unpack_from('<8I',image,8)
 if (ka,ra,tags,page,ss)!=(0x10008000,0x11000000,0x10000100,2048,0): raise SystemExit('unexpected boot layout')
 kernel=image[page:page+ks]
 runtime=parse_newc(a.runtime_source.read_bytes())
 busybox=runtime['bin/busybox'].data
 usb_loop=runtime['bin/usb-report-loop'].data
 checker=a.checker.read_bytes()
 if not checker.startswith(b'\x7fELF'): raise SystemExit('checker is not ELF')
 fixtures={n:(a.fixtures/n).read_bytes() for n in ('clean.img.xz','counter.img.xz')}
 scripts={n:(ROOT/'diagnostic'/n).read_bytes() for n in
          ('offline97-init.sh','offline97-ramtest.sh','offline97-report.sh','offline97-server.sh')}
 entries={}
 for d in ('bin','dev','fixtures','proc','run','sys','tmp'):
  entries[d]=Entry(d,stat.S_IFDIR|0o755)
 entries['init']=Entry('init',stat.S_IFREG|0o755,scripts['offline97-init.sh'])
 entries['bin/busybox']=Entry('bin/busybox',stat.S_IFREG|0o755,busybox)
 entries['bin/usb-report-loop']=Entry('bin/usb-report-loop',stat.S_IFREG|0o755,usb_loop)
 entries['bin/offline97-ramtest']=Entry('bin/offline97-ramtest',stat.S_IFREG|0o755,scripts['offline97-ramtest.sh'])
 entries['bin/diagnostic-report']=Entry('bin/diagnostic-report',stat.S_IFREG|0o755,scripts['offline97-report.sh'])
 entries['bin/diagnostic-server']=Entry('bin/diagnostic-server',stat.S_IFREG|0o755,scripts['offline97-server.sh'])
 entries['bin/e2fsck']=Entry('bin/e2fsck',stat.S_IFREG|0o755,checker)
 for n,b in fixtures.items(): entries['fixtures/'+n]=Entry('fixtures/'+n,stat.S_IFREG|0o644,b)
 cpio=pack_newc(entries)
 ram=cpio if a.uncompressed else lzma.compress(cpio,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC32)
 boot=boot_image(kernel,ram)
 a.output_dir.mkdir(mode=0o755)
 (a.output_dir/'wingray-offline97-readonly.img').write_bytes(boot)
 (a.output_dir/('initramfs.cpio' if a.uncompressed else 'initramfs.cpio.xz')).write_bytes(ram)
 manifest={'image':'wingray-offline97-readonly.img','image_sha256':sha(boot),'image_bytes':len(boot),
  'kernel_sha256':sha(kernel),'ramdisk_sha256':sha(ram),'checker_sha256':sha(checker),
  'checker_bytes':len(checker),'fixtures':{n:sha(b) for n,b in fixtures.items()},
  'physical_writes':False,'android':False,'twrp':False,'mass_storage':False,
  'cache':False,'p9_p10_policy':'read-only','hardware_validated':False}
 (a.output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2))
if __name__=='__main__': main()
