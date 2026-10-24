#!/usr/bin/env python3
"""Pack a bounded offscreen GPU test entirely in RAM; no device operations."""
from pathlib import Path
import argparse, gzip, hashlib, json, re, stat, struct, subprocess
from android44_image import (Entry, original_entries, default_properties,
                             pack_newc, parse_newc, boot_image, BUSYBOX_SHA256)
from gpu_test import validate_artifacts

ROOT = Path(__file__).resolve().parents[1]
TRACE_SHA = 'cdd7ab77abfe739b6425eaa1eb7644ec8f019579fbc65ef90734b49854968875'
PROBE_SHA = '606d7757d6b290599bb3e6c0f7de8f88d35c91d66ac17df591b29582e37abb1d'
RECOVERY_SHA = '5545aea043eaa9f8ac37b27103ddf202e5cf3bb56ee040cbc94712a8ca39e606'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def fnv1a32(data):
    value = 2166136261
    for byte in data:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value

def runtime_files():
    private = ROOT/'artifacts/hardware-private'
    trace = (ROOT/'artifacts/original-egl-submission46-raw/submission-trace-private.txt').read_bytes()
    assert sha(trace) == TRACE_SHA
    files = {
        'bin/busybox': ROOT/'artifacts/busybox-static-armv5l',
        'system/bin/linker': private/'linker',
        'system/bin/sh': ROOT/'artifacts/gpu-runtime48-inputs/android-sh',
        'system/lib/xoom-egl-probe.so': ROOT/'artifacts/kitkat-egl-probe41-v2/xoom-egl-probe.so',
    }
    assert sha(files['bin/busybox'].read_bytes()) == BUSYBOX_SHA256
    assert sha(files['system/lib/xoom-egl-probe.so'].read_bytes()) == PROBE_SHA
    # Only successfully opened original-ROM libraries; no decoded command replay.
    for line in trace.decode().splitlines():
        m = re.search(r'open\("((?:\\x[0-9a-f]{2})+)".*\)\s+= \d+$', line)
        if not m:
            continue
        name = bytes.fromhex(m[1].replace('\\x', '')).decode()
        if name.startswith('/system/lib/') and name.endswith('.so'):
            files[name[1:]] = private/'system-lib'/name.removeprefix('/system/lib/')
    assert len([n for n in files if n.startswith('system/lib/')]) == 28
    pending = list(files.values())
    while pending:
        path = pending.pop()
        data = path.read_bytes()
        assert data[:7] == b'\x7fELF\x01\x01\x01' and struct.unpack_from('<H', data, 18)[0] == 40, path
        dynamic = subprocess.check_output(['readelf', '-dW', str(path)], text=True)
        for lib in re.findall(r'Shared library: \[([^\]]+)\]', dynamic):
            assert '/' not in lib and lib.endswith('.so')
            name = 'system/lib/'+lib
            if name not in files:
                files[name] = private/'system-lib'/lib
                pending.append(files[name])
    assert not any('GLES_android' in n or 'swiftshader' in n.lower() for n in files)
    return files

def entries(files, *, startup_trace=False, render_probe=False, deferred_probe=False):
    assert not deferred_probe or render_probe
    assert not render_probe or startup_trace
    original = original_entries((ROOT/'artifacts/hardware-private/backup-boot.img').read_bytes())
    e = {}
    for name in ('.', 'ueventd.rc', 'ueventd.stingray.rc', 'file_contexts',
                 'property_contexts', 'sepolicy', 'seapp_contexts'):
        e[name] = original[name]
    item = original['init']
    e['init.android'] = Entry('init.android', item.mode, item.data)
    for name in ('bin', 'sbin', 'system', 'system/bin', 'system/lib', 'system/lib/egl',
                 'system/lib/hw', 'dev', 'proc', 'sys', 'run', 'tmp', 'data', 'cache'):
        e[name] = Entry(name, stat.S_IFDIR | 0o755)
    for name, target in {'bin/sh': 'busybox', 'sbin/ueventd': '/init.android',
                         'vendor': '/system/vendor'}.items():
        e[name] = Entry(name, stat.S_IFLNK | 0o777, target.encode())
    for name, path in files.items():
        e[name] = Entry(name, stat.S_IFREG | 0o755, path.read_bytes())
    scripts = {'init': 'gpu-render-init.sh', 'bin/gpu-render-start': 'gpu-render-start.sh',
               'bin/gpu-render-report': 'gpu-render-report.sh',
               'bin/diagnostic-server': 'server.sh', 'bin/usb-report-loop': 'usb-report-loop.sh'}
    for name, path in scripts.items():
        e[name] = Entry(name, stat.S_IFREG | 0o755, (ROOT/'diagnostic'/path).read_bytes())
    report = (ROOT/'diagnostic/report.sh').read_bytes()
    anchor = b"/bin/busybox printf 'XOOM_DMESG_BEGIN"
    assert report.count(anchor) == 1
    e['bin/diagnostic-report'] = Entry('bin/diagnostic-report', stat.S_IFREG | 0o755,
        report.replace(anchor, b'/bin/busybox sh /bin/gpu-render-report\n'+anchor))
    e['init.rc'] = Entry('init.rc', stat.S_IFREG | 0o644, (ROOT/'diagnostic/gpu-render.rc').read_bytes())
    if startup_trace:
        def alter(name, data):
            e[name] = Entry(name, e[name].mode, data)
        def marker(value):
            return (b'[ ! -c /dev/xoom-startup-trace ] || /bin/busybox printf "'+value+
                    b'\\n" > /dev/xoom-startup-trace\n')
        init = e['init'].data
        anchor = b'/bin/busybox mount -t devtmpfs devtmpfs /dev || fail dev\n'
        assert init.count(anchor) == 1
        init = init.replace(anchor, anchor+marker(b'1'))
        init = init.replace(b'exec /init.android', marker(b'2')+b'exec /init.android')
        alter('init', init)
        if not render_probe:
            rc = e['init.rc'].data.replace(b'gpu-probe', b'gpu-startup').replace(
                b'/bin/gpu-render-start', b'/bin/gpu-startup-check')
            alter('init.rc', rc)
            e.pop('bin/gpu-render-start')
            e['bin/gpu-startup-check'] = Entry('bin/gpu-startup-check', stat.S_IFREG | 0o755,
                (ROOT/'diagnostic/gpu-startup-check.sh').read_bytes())
        else:
            render = marker(b'3')+e['bin/gpu-render-start'].data.removeprefix(b'#!/bin/busybox sh\n')
            render = b'#!/bin/busybox sh\n'+render
            anchor = b'/bin/busybox timeout -s KILL 35 '
            assert render.count(anchor)==1
            render=render.replace(anchor,marker(b'4')+anchor)
            render=render.replace(b'result=$?\n',b'result=$?\n'+marker(b'5'))
            if deferred_probe:
                anchor=b'/bin/busybox cat /proc/interrupts > /run/gpu-interrupts-before.txt\n'
                assert render.count(anchor)==1
                gate=(b'echo XOOM_GPU_RENDER_WAIT_USB_GATE\n'
                      b': > /run/gpu-probe-ready\n'
                      b'gate_wait=0\n'
                      b'while [ ! -e /run/gpu-probe-release ]; do\n'
                      b' if [ "$gate_wait" -ge 300 ]; then\n'
                      b'  /bin/busybox rm -f /run/gpu-probe-ready\n'
                      b'  echo XOOM_GPU_RENDER_GATE_TIMEOUT\n'
                      b'  exit 3\n'
                      b' fi\n'
                      b' /bin/busybox sleep 1\n'
                      b' gate_wait=$((gate_wait + 1))\n'
                      b'done\n')
                render=render.replace(anchor,gate+anchor)
            alter('bin/gpu-render-start',render)
        loop = e['bin/usb-report-loop'].data
        loop = loop.replace(b'echo -1000', marker(b'A')+b'xoom_trace_usb_seen=0\necho -1000', 1)
        loop = loop.replace(b' if [ -c /dev/ttyGS0 ]; then\n',
                            b' if [ -c /dev/ttyGS0 ]; then\n'
                            b'  if [ "$xoom_trace_usb_seen" -eq 0 ]; then\n'+marker(b'B')+
                            b'   xoom_trace_usb_seen=1\n  fi\n', 1)
        alter('bin/usb-report-loop', loop)
        server = e['bin/diagnostic-server'].data
        server = server.replace(b' if [ "$verb" = PING ]; then', marker(b'C')+
                                b' if [ "$verb" = PING ]; then', 1)
        if deferred_probe:
            server=server.replace(b"# One fixed read-only request.",b"# Fixed PING/REPORT reads; GPU_RUN releases one preconfigured RAM-only child.")
            anchor=b'  PING\\ *) verb=PING; nonce=${request#PING } ;;\n'
            assert server.count(anchor)==1
            server=server.replace(anchor,anchor+b'  GPU_RUN\\ *) verb=GPU_RUN; nonce=${request#GPU_RUN } ;;\n')
            anchor=b' if [ "$verb" = PING ]; then'
            assert server.count(anchor)==1
            command=(b' if [ "$verb" = GPU_RUN ]; then\n'
                     b'  if [ -e /run/gpu-probe-release ]; then\n'
                     b'   /bin/busybox printf "XOOM_GPU_RELEASE_V1 %s ALREADY\\n" "$nonce"\n'
                     b'  elif [ ! -e /run/gpu-probe-ready ]; then\n'
                     b'   /bin/busybox printf "XOOM_GPU_RELEASE_V1 %s NOT_READY\\n" "$nonce"\n'
                     b'  else\n'
                     b'   /bin/busybox printf "XOOM_GPU_RELEASE_V1 %s ARMED\\n" "$nonce"\n'
                     b'   (umask 077; set -C; : > /run/gpu-probe-release)\n'
                     b'  fi\n'
                     b'  continue\n'
                     b' fi\n')
            server=server.replace(anchor,command+anchor)
        alter('bin/diagnostic-server', server)
    e['default.prop'] = Entry('default.prop', stat.S_IFREG | 0o644,
        default_properties(original['default.prop'].data)+b'ro.board.platform=tegra\nro.product.device=wingray\n')
    e['system/build.prop'] = Entry('system/build.prop', stat.S_IFREG | 0o644,
        (ROOT/'artifacts/lockscreen-reference-28/additional-runtime/build.prop').read_bytes())
    for name, major, minor in [('console', 5, 1), ('null', 1, 3)]:
        e['dev/'+name] = Entry('dev/'+name, stat.S_IFCHR | 0o600, major=major, minor=minor)
    assert parse_newc(pack_newc(e)) == e
    assert not any(n.startswith('fstab') or n.startswith('init.') and n not in {'init.android', 'init.rc'} for n in e)
    assert 'import ' not in e['init.rc'].data.decode()
    assert not any(x in e['init.rc'].data for x in (b'mount ', b'class_start', b'zygote', b'surfaceflinger'))
    return e

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kernel-dir', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--startup-trace', action='store_true',
                   help='Require trace cookie 49 and replace rendering with startup-only checks')
    p.add_argument('--trace-cookie',type=lambda v:int(v,0),choices=(0x584d0049,0x584d0050,0x584d0051,0x584d0052,0x584d0053,0x584d0054,0x584d0055,0x584d0056),default=0x584d0049)
    p.add_argument('--deferred-probe', action='store_true', help='Only cookie 56: require explicit fixed GPU_RUN after a baseline USB report')
    p.add_argument('--render-probe', action='store_true', help='Cookies 55/56: bounded child offscreen probe in built-in runtime')
    p.add_argument('--ramdisk-address', type=lambda v:int(v,0), choices=(0x11000000,0x12000000), default=0x11000000)
    a = p.parse_args(); out = a.output_dir.resolve()
    assert a.startup_trace or a.trace_cookie==0x584d0049
    assert not a.render_probe or a.startup_trace and a.trace_cookie in (0x584d0055,0x584d0056)
    assert a.trace_cookie not in (0x584d0055,0x584d0056) or a.render_probe
    assert a.deferred_probe == (a.trace_cookie==0x584d0056)
    assert out.is_relative_to(ROOT/'artifacts') and not out.exists()
    validate_artifacts(a.kernel_dir, startup_trace=a.startup_trace, trace_cookie=a.trace_cookie)
    recovery = ROOT/'artifacts/hardware-private/backup-recovery.img'
    assert sha(recovery.read_bytes()) == RECOVERY_SHA
    files = runtime_files(); archive = pack_newc(entries(files, startup_trace=a.startup_trace, render_probe=a.render_probe, deferred_probe=a.deferred_probe))
    builtin_runtime = a.startup_trace and a.trace_cookie in (0x584d0054,0x584d0055,0x584d0056)
    runtime_archive_sha = sha(archive)
    if builtin_runtime:
        assert gzip.decompress((a.kernel_dir/'builtin-initramfs.cpio.gz').read_bytes()) == archive
        archive = pack_newc({})  # Valid trailer only; cannot override built-in files.
    assert len(archive) < 16*1024*1024
    ramdisk = gzip.compress(archive, mtime=0)
    kernel = (a.kernel_dir/'zImage-dtb').read_bytes()
    image = boot_image(kernel, ramdisk)
    if a.ramdisk_address != 0x11000000:
        # A controlled header-only relocation; leave the tested common packer alone.
        assert a.startup_trace and a.trace_cookie == 0x584d0053
        assert a.ramdisk_address + len(ramdisk) < 0x1fe00000
        control = image
        image = bytearray(control)
        struct.pack_into('<I', image, 20, a.ramdisk_address)
        image = bytes(image)
        assert image[:20] == control[:20] and image[24:] == control[24:]
    assert len(image) < 8*1024*1024
    manifest = {'purpose': 'fixed-clock NVIDIA offscreen two-frame readback, not Android composition',
        'hardware_executed': False, 'acceleration_proven': False,
        'ramdisk_load_address': hex(a.ramdisk_address),
        'startup_trace_only': a.startup_trace and not a.render_probe,
        'retained_startup_trace': a.startup_trace, 'rendering_enabled': a.render_probe or not a.startup_trace,
        'deferred_probe': a.deferred_probe, 'builtin_runtime': builtin_runtime, 'runtime_archive_sha256': runtime_archive_sha,
        'trace_cookie': hex(a.trace_cookie) if a.startup_trace else None,
        'sha256': sha(image), 'size': len(image), 'kernel_sha256': sha(kernel),
        'ramdisk_sha256': sha(ramdisk), 'ramdisk_uncompressed_size': len(archive),
        'ramdisk_size': len(ramdisk), 'ramdisk_fnv1a32': f'{fnv1a32(ramdisk):08x}',
        'runtime_sha256': {n: sha(p.read_bytes()) for n, p in sorted(files.items())},
        'storage_mounts': [], 'services': ['ueventd', 'gpu-startup' if a.startup_trace and not a.render_probe else 'gpu-probe'],
        'probe_timeout_seconds': None if a.startup_trace and not a.render_probe else 35, 'trace_sha256': TRACE_SHA,
        'source_sha256': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
            [Path(__file__).resolve(), ROOT/'scripts/gpu_test.py', ROOT/'scripts/android44_image.py',
             *[ROOT/'diagnostic'/n for n in ['gpu-render-init.sh', 'gpu-render-start.sh', 'gpu-startup-check.sh',
                'gpu-render-report.sh', 'gpu-render.rc', 'server.sh', 'usb-report-loop.sh', 'report.sh']]]}}
    out.mkdir()
    if a.startup_trace and not a.render_probe:
        manifest['purpose'] = 'retained startup checkpoints only; GPU rendering is disabled'
    (out/'ramdisk.cpio.gz').write_bytes(ramdisk)
    (out/'wingray-gpu-render-diagnostic.img').write_bytes(image)
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    assert sha(recovery.read_bytes()) == RECOVERY_SHA
    print('Prepared RAM-only GPU test; not flashed:', out, 'bytes:', len(image))

if __name__ == '__main__':
    main()
