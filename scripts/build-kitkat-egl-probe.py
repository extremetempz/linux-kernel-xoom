#!/usr/bin/env python3
"""Build an optional EGL client against preserved owner KitKat libraries.

No flash, device access, boot packaging, automatic execution or redistribution
of vendor libraries. Standard Khronos declarations come from installed headers;
only ES2/EGL1.4 entry points already used by the original probe are linked.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output-dir',type=Path,required=True)
a=p.parse_args();out=a.output_dir.resolve()
assert out.is_relative_to(root/'artifacts') and not out.exists()
lib=root/'artifacts/hardware-private/system-lib';cc=root/'toolchains/android-gcc49/bin/arm-linux-androideabi-gcc'
out.mkdir();inc=out/'include';inc.mkdir()
headers=['EGL/egl.h','EGL/eglplatform.h','GLES2/gl2.h','GLES2/gl2platform.h','KHR/khrplatform.h']
for name in headers:
 target=inc/name;target.parent.mkdir(exist_ok=True);shutil.copyfile('/usr/include/'+name,target)
source=root/'diagnostic/egl-probe'
flags=['-Os','-Wall','-Wextra','-Werror','-fPIC','-ffreestanding','-fno-stack-protector','-marm','-march=armv7-a','-mfloat-abi=softfp','-mfpu=vfpv3-d16','-DXOOM_EGL_KITKAT_ABI','-DEGL_NO_PLATFORM_SPECIFIC_TYPES','-I'+str(inc),'-I'+str(source)]
for filename,obj,extra in [('egl-probe.c','probe.o',['-Dmain=xoom_egl_probe_main']),('preload-entry.c','entry.o',[])]:
 subprocess.run([str(cc),*flags,*extra,'-c',str(source/filename),'-o',str(out/obj)],check=True)
module=out/'xoom-egl-probe.so'
libgcc=subprocess.check_output([str(cc),'-marm','-march=armv7-a','-mfloat-abi=softfp','-mfpu=vfpv3-d16','-print-libgcc-file-name'],text=True).strip()
subprocess.run([str(cc.parent/'arm-linux-androideabi-ld'),'-shared','--no-undefined','-z','noexecstack','--build-id=none','-soname','xoom-egl-probe.so',str(lib/'crtbegin_so.o'),str(out/'probe.o'),str(out/'entry.o'),'-L'+str(lib),'-rpath-link',str(lib),'-lEGL','-lGLESv2','-lc',libgcc,str(lib/'crtend_so.o'),'-o',str(module)],check=True)
program=subprocess.check_output(['readelf','-lW',str(module)],text=True)
attrs=subprocess.check_output(['readelf','-A',str(module)],text=True)
dynamic=subprocess.check_output(['readelf','-dW',str(module)],text=True)
assert module.read_bytes()[:7]==b'\x7fELF\x01\x01\x01' and module.read_bytes()[18:20]==b'\x28\0'
assert 'INTERP' not in program and 'Tag_CPU_arch: v7' in attrs and 'Tag_Advanced_SIMD_arch:' not in attrs
assert 'TEXTREL' not in dynamic
for x in ['libEGL.so','libGLESv2.so','libc.so']:assert x in dynamic
manifest={'purpose':'manual isolated-child EGL probe, not a driver or boot image','hardware_executed':False,'new_kernel_acceleration_proven':False,'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),'sources':{name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in ['egl-probe.c','preload-entry.c','kitkat-c-api.h']},'public_headers':{name:hashlib.sha256((inc/name).read_bytes()).hexdigest() for name in headers},'link_inputs':{name:hashlib.sha256((lib/name).read_bytes()).hexdigest() for name in ['crtbegin_so.o','crtend_so.o','libEGL.so','libGLESv2.so','libc.so']},'limits':['Only isolated child with explicit XOOM_EGL_PROBE_CHILD=1; never preload Android services.','Requires matching installed libraries and working kernel graphics interfaces.','Original-ROM success does not prove new-kernel acceleration.']}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Built ARMv7 non-NEON KitKat ELF module. Not executed; no boot image or flash action.')
