#!/usr/bin/env python3
"""Assemble a local-only experimental boot image; no device operations or flashing."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess

from android44_image import (BUSYBOX_SHA256, boot_image, digest, original_entries,
                             pack_newc, ramdisk_entries)

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'artifacts/lockscreen-reference-28'


def check_static_arm(path, cpu):
    data = path.read_bytes()
    if data[:7] != b'\x7fELF\x01\x01\x01' or data[18:20] != b'\x28\0':
        raise ValueError('Require little-endian ELF32 ARM: ' + path.name)
    headers = subprocess.check_output(['readelf', '-lW', str(path)], text=True)
    dynamic = subprocess.check_output(['readelf', '-dW', str(path)], text=True)
    attributes = subprocess.check_output(['readelf', '-A', str(path)], text=True)
    if ('INTERP' in headers or '(NEEDED)' in dynamic or
            f'Tag_CPU_arch: {cpu}\n' not in attributes or 'Tag_Advanced_SIMD_arch:' in attributes):
        raise ValueError('Unexpected static-runtime architecture/dependencies: ' + path.name)
    if subprocess.check_output(['nm', '-u', str(path)], text=True, stderr=subprocess.DEVNULL).strip():
        raise ValueError('Runtime has undefined symbols: ' + path.name)
    return data


def checked_runtime(directory, name, source, expected_release=None, kernel_config=None):
    path = directory / name
    manifest = json.loads((directory / f'{name}-manifest.json').read_text())
    data = check_static_arm(path, 'v7')
    if digest(data) != manifest['sha256'] or digest(source.read_bytes()) != manifest['source_sha256']:
        raise ValueError('Stale or mismatched runtime manifest: ' + name)
    if name == 'android44-abi-probe' and manifest['expected_binder_protocol'] != 7:
        raise ValueError('Wrong Binder ABI')
    if expected_release is not None:
        if manifest.get('expected_release') != expected_release or expected_release.encode() + b'\0' not in data:
            raise ValueError('Runtime compiled for a different kernel release: ' + name)
    if kernel_config is not None and manifest.get('kernel_config_sha256') != digest(kernel_config):
        raise ValueError('ABI probe was not built against this kernel configuration')
    return data


def system_hashes():
    """Hash only previously saved fixed ROM references; never read a live device."""
    references = {
        '/system/build.prop': REFERENCE / 'additional-runtime/build.prop',
        '/system/bin/surfaceflinger': REFERENCE / 'graphics-elf/surfaceflinger',
        '/system/lib/libEGL.so': REFERENCE / 'graphics-elf/libEGL.so',
        '/system/lib/libsurfaceflinger.so': REFERENCE / 'graphics-elf/libsurfaceflinger.so',
        '/system/lib/libandroid_runtime.so': REFERENCE / 'additional-runtime/libandroid_runtime.so',
        '/system/lib/libhwui.so': REFERENCE / 'additional-runtime/libhwui.so',
        '/system/lib/egl/libGLES_android.so': REFERENCE / 'graphics-elf/libGLES_android.so',
        '/system/lib/hw/gralloc.default.so': REFERENCE / 'graphics-elf/gralloc.default.so',
    }
    for name in ('audio.primary.default', 'audio_policy.default', 'power.default',
                 'keystore.default', 'local_time.default'):
        references[f'/system/lib/hw/{name}.so'] = REFERENCE / f'default-hals/{name}.so'
    hashes = {name: digest(path.read_bytes()) for name, path in sorted(references.items())}
    return ''.join(f'{sha}  {name}\n' for name, sha in hashes.items()).encode(), hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--kernel-dir', type=Path, default=ROOT / 'artifacts/candidate-30-guarded')
    parser.add_argument('--runtime-dir', type=Path, default=ROOT / 'artifacts/candidate-30-guarded')
    parser.add_argument('--profile', choices=('android44', 'android44-touch'), default='android44')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / 'artifacts').resolve()) or output.exists():
        parser.error('Require a new directory under ignored artifacts/; never overwrite evidence')
    # Every prerequisite is checked before the output directory is created.
    subprocess.run(['python3', str(ROOT / 'scripts/verify-kernel.py'), str(args.kernel_dir), args.profile], check=True)
    release = '4.4.147-wingray-' + args.profile
    config = (args.kernel_dir / 'kernel.config').read_bytes()
    backup = (ROOT / 'artifacts/hardware-private/backup-boot.img').read_bytes()
    original = original_entries(backup)
    busybox_path = ROOT / 'artifacts/busybox-static-armv5l'
    busybox = check_static_arm(busybox_path, 'v5T')
    if digest(busybox) != BUSYBOX_SHA256:
        raise ValueError('Pinned BusyBox hash mismatch')
    hashes_text, hashes = system_hashes()
    files = {
        'bin/busybox': busybox,
        'bin/android44-abi-probe': checked_runtime(args.runtime_dir, 'android44-abi-probe', ROOT / 'diagnostic/android44-abi-probe.c', release, config),
        'bin/display-pattern': checked_runtime(args.runtime_dir, 'display-pattern', ROOT / 'diagnostic/display-pattern.c'),
        'bin/android44-system-sha256': hashes_text,
    }
    helpers = {
        'init': 'android44-init.sh', 'bin/android44-bootstrap': 'android44-bootstrap.sh',
        'bin/android-service-runner': 'android-service-runner.sh',
        'bin/usb-report-loop': 'usb-report-loop.sh', 'bin/diagnostic-server': 'server.sh',
        'bin/diagnostic-report': 'report.sh', 'bin/android44-report': 'android44-report.sh',
        'bin/display-report': 'display-report.sh',
    }
    if args.profile == 'android44-touch':
        files['bin/touch-events'] = checked_runtime(args.runtime_dir, 'touch-events', ROOT / 'diagnostic/touch-events.c', release, config)
        helpers['bin/touch-report'] = 'touch-report.sh'
    for name, source in helpers.items():
        path = ROOT / 'diagnostic' / source
        subprocess.run(['bash', '-n', str(path)], check=True)
        files[name] = path.read_bytes()
    entries = ramdisk_entries(original, files)
    archive = pack_newc(entries)
    ramdisk = gzip.compress(archive, mtime=0)
    kernel = (args.kernel_dir / 'zImage-dtb').read_bytes()
    image = boot_image(kernel, ramdisk)
    manifest = {
        'purpose': 'offline-prepared Android 4.4 RAM-data experiment; no device operations',
        'hardware_tested': False, 'android_booted': False,
        'kernel_profile': args.profile, 'expected_kernel_release': release,
        'touch_diagnostics': args.profile == 'android44-touch',
        'storage_mode': 'android44-readonly',
        'storage_policy': 'software read-only eMMC; system ro,noload; tmpfs data/cache; no persistent writes intended',
        'graphics_policy': 'fixed RGB mode; RAM-only default HAL and exact software GLES overlay; custom ROM fallback untested',
        'size': len(image), 'sha256': digest(image),
        'original_boot_sha256': digest(backup), 'kernel_sha256': digest(kernel),
        'ramdisk_sha256': digest(ramdisk),
        'runtime_sha256': {name: digest(data) for name, data in files.items()},
        'system_reference_sha256': hashes,
        'archive': [{'name': e.name, 'mode': oct(e.mode), 'uid': e.uid, 'gid': e.gid,
                     'size': len(e.data), 'sha256': digest(e.data)} for e in entries.values()],
        'limits': ['No target Android startup or ABI validation yet.',
                   'Input is experimental only in the touch profile; GPU acceleration/wake alarms/suspend remain unvalidated.',
                   'RAM data is temporary; first DEX generation may exceed available memory.',
                   'Only fixed previously saved system references are hashed, not the whole system partition.'],
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / 'wingray-android44-ramdata.img').write_bytes(image)
    (output / 'ramdisk.cpio.gz').write_bytes(ramdisk)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Generated text is private review material: do not upload the copied ROM.
    review = output / 'generated'
    review.mkdir()
    for name in ('init.rc', 'init.xoom-firstboot.rc', 'default.prop', 'fstab.stingray'):
        (review / name).write_bytes(entries[name].data)
    print('Prepared locally, NOT flashed:', output / 'wingray-android44-ramdata.img')
    print('SHA256:', digest(image))


if __name__ == '__main__':
    main()
