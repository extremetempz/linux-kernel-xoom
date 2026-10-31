"""Bounded, nonce-correlated diagnostic transport. FBTEST is a fixed framebuffer write test."""
import base64
import binascii
from collections import Counter
import hashlib
import os
from pathlib import Path
import re
import select
import time

MAX_PAYLOAD = 524288
MAX_WIRE = MAX_PAYLOAD * 2 + 4096
NONCE = re.compile(r'[0-9a-f]{32}\Z')

class ProtocolError(ValueError):
    pass

def _nonce(value):
    if not NONCE.fullmatch(value):
        raise ProtocolError('Nonce must be exactly 32 lowercase hex digits')
    return value.encode('ascii')

def write_request(fd, verb, nonce, timeout=2):
    if verb not in ('PING', 'REPORT', 'FBTEST', 'PSTORE', 'DCTEST', 'WAKETEST', 'FREEZERTEST', 'DEVICEPMTEST', 'DPMTEST', 'DPMSTATUS', 'BOOTID', 'CPU1TEST'):
        raise ProtocolError('Only PING, REPORT, FBTEST, PSTORE, DCTEST, WAKETEST, FREEZERTEST, DEVICEPMTEST, DPMTEST, DPMSTATUS, BOOTID and CPU1TEST are permitted')
    data = verb.encode() + b' ' + _nonce(nonce) + b'\n'
    deadline = time.monotonic() + timeout
    while data:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
            raise TimeoutError('Timed out sending diagnostic request')
        try:
            count = os.write(fd, data)
        except BlockingIOError:
            continue
        if count <= 0:
            raise ProtocolError('Serial port closed while sending request')
        data = data[count:]

def _read(fd, deadline, record):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Timed out waiting for diagnostic response')
    if not select.select([fd], [], [], min(remaining, 1))[0]:
        return b''
    try:
        data = os.read(fd, 65536)
    except BlockingIOError:
        return b''
    if not data:
        raise ProtocolError('Serial device disconnected')
    if record:
        record(data)
    return data

def handshake(fd, nonce, timeout=15, record=None):
    token = _nonce(nonce)
    expected = re.compile(rb'(?:^|\n)XOOM_READY_V2 ' + token + rb'\r?\n')
    deadline = time.monotonic() + timeout
    next_ping = 0
    buffer = bytearray()
    while time.monotonic() < deadline:
        if time.monotonic() >= next_ping:
            write_request(fd, 'PING', nonce)
            next_ping = time.monotonic() + 1
        buffer.extend(_read(fd, deadline, record))
        if expected.search(buffer):
            return
        if len(buffer) > 4096:
            raise ProtocolError('Unexpected unsolicited output; framed reporter not established')
    raise TimeoutError('Diagnostic readiness handshake timed out')

class FrameDecoder:
    def __init__(self, nonce):
        token = _nonce(nonce)
        self.nonce = nonce
        self.header = re.compile(rb'(?:^|\n)XOOM_REPORT_V2 ' + token + rb' ([0-9]{1,6}) ([0-9a-f]{64})\r?\n')
        self.end = re.compile(rb'(?:^|\n)XOOM_END_V2 ' + token + rb'\r?\n')
        self.error = re.compile(rb'(?:^|\n)XOOM_ERROR_V2 ' + token + rb' ([A-Z_]+)\r?\n')
        self.buffer = bytearray()
        self.payload = None

    def feed(self, data):
        if self.payload is not None:
            raise ProtocolError('Frame already completed')
        self.buffer.extend(data)
        if len(self.buffer) > MAX_WIRE:
            raise ProtocolError('Diagnostic wire-size limit exceeded')
        error = self.error.search(self.buffer)
        if error:
            raise ProtocolError('Device report error: ' + error[1].decode('ascii'))
        header = self.header.search(self.buffer)
        if not header:
            if len(self.buffer) > 4096:
                raise ProtocolError('No matching response header within prefix limit')
            return None
        size = int(header[1])
        if not 0 < size <= MAX_PAYLOAD:
            raise ProtocolError('Declared payload size is outside the permitted bound')
        end = self.end.search(self.buffer, header.end())
        if not end:
            return None
        body = self.buffer[header.end():end.start()]
        try:
            payload = base64.b64decode(b''.join(body.split()), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ProtocolError('Invalid report base64') from exc
        if len(payload) != size:
            raise ProtocolError('Report byte count does not match header')
        if hashlib.sha256(payload).hexdigest().encode() != header[2]:
            raise ProtocolError('Report SHA-256 does not match header')
        nonce = self.nonce.encode()
        if not payload.startswith(b'XOOM_FRESH_REPORT_V2 ' + nonce + b'\n'):
            raise ProtocolError('Payload request identity is missing or stale')
        if not payload.endswith(b'XOOM_FRESH_REPORT_DONE ' + nonce + b'\n'):
            raise ProtocolError('Payload completion marker is missing')
        self.payload = payload
        return payload

def receive_report(fd, nonce, timeout=45, record=None):
    decoder = FrameDecoder(nonce)
    deadline = time.monotonic() + timeout
    while True:
        payload = decoder.feed(_read(fd, deadline, record))
        if payload is not None:
            return payload

def expected_geometry(path):
    lines = Path(path).read_text().splitlines()
    result = {}
    if len(lines) != 30:
        raise ProtocolError('Expected a complete ten-partition reference')
    for index in range(0, len(lines), 3):
        match = re.fullmatch(r'/sys/block/mmcblk0/(mmcblk0p(?:10|[1-9]))', lines[index])
        if not match or match[1] in result:
            raise ProtocolError('Invalid or duplicate reference partition')
        if not lines[index+1].isdigit() or not lines[index+2].isdigit():
            raise ProtocolError('Invalid reference geometry')
        result[match[1]] = (int(lines[index+1]), int(lines[index+2]))
    return result

def _section(text, begin, end):
    """Require one complete metadata section, rather than accept stale duplicates."""
    if text.count(begin + '\n') != 1 or text.count(end + '\n') != 1:
        raise ProtocolError('Missing or duplicate ' + begin + ' section')
    match = re.search(r'^' + re.escape(begin) + r'\n(.*?)^' + re.escape(end) + r'\n',
                      text, re.M | re.S)
    if not match:
        raise ProtocolError('Malformed ' + begin + ' section')
    return match[1]


def _mountinfo(text):
    records = []
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        try:
            separator = fields.index('-')
        except ValueError as exc:
            raise ProtocolError('Malformed Android mountinfo') from exc
        if (separator < 6 or len(fields) != separator + 4
                or not fields[0].isdigit() or not fields[1].isdigit()
                or not re.fullmatch(r'[0-9]+:[0-9]+', fields[2])):
            raise ProtocolError('Malformed Android mountinfo')
        records.append({'device': fields[2], 'root': fields[3], 'target': fields[4],
                        'options': set(fields[5].split(',')), 'fstype': fields[separator+1],
                        'source': fields[separator+2],
                        'super_options': set(fields[separator+3].split(','))})
    return records


def _android44_mount_policy(text, mounts):
    """Validate the isolated, RAM-data Android experiment, never general ROM mounts.

    This is evidence validation, not an additional device write-protection layer.
    Snapshots are not atomic; a bootstrap mount transition may require a new report.
    """
    if re.findall(r'^XOOM_ANDROID44_REPORT_DONE_V1$', text, re.M) != ['XOOM_ANDROID44_REPORT_DONE_V1']:
        raise ProtocolError('Android report helper did not complete exactly once')
    policy = _section(text, 'XOOM_ANDROID44_POLICY_BEGIN_V1', 'XOOM_ANDROID44_POLICY_END_V1')
    releases = re.findall(r'^XOOM_ANDROID44_RELEASE (.*)$', policy, re.M)
    if len(releases) != 1 or releases[0] not in ('4.4.147-wingray-android44', '4.4.147-wingray-android44-touch', '4.4.147-wingray-android44-l2', '4.4.147-wingray-android44-smp', '4.4.147-wingray-android44-smp2', '4.4.147-wingray-android44-smptrace', '4.4.147-wingray-android44-gpu'):
        raise ProtocolError('Android read-only mode requires the exact Android44 kernel release')
    if re.findall(r'^XOOM_ANDROID44_BOARD (.*)$', policy, re.M) != ['motorola,wingray']:
        raise ProtocolError('Android read-only mode requires the Wingray board identity')
    wanted = {'mmcblk0', *(f'mmcblk0p{i}' for i in range(1, 11))}
    flags = re.findall(r'^XOOM_ANDROID44_BLOCK_RO (\S+) (\S+)$', policy, re.M)
    if len(flags) != 11 or dict(flags) != dict.fromkeys(wanted, '1'):
        raise ProtocolError('Android mode requires all eleven eMMC read-only flags')
    info = _mountinfo(_section(policy, 'XOOM_ANDROID44_MOUNTINFO_BEGIN',
                              'XOOM_ANDROID44_MOUNTINFO_END'))
    if Counter((m['source'], m['target'], m['fstype']) for m in info) != Counter(
            (m[0], m[1], m[2]) for m in mounts):
        raise ProtocolError('Android mounts and mountinfo snapshots disagree; request a fresh report')

    by_target = {}
    for record in info:
        by_target.setdefault(record['target'], []).append(record)

    def unique(target, required=False):
        records = by_target.get(target, [])
        if len(records) > 1 or (required and len(records) != 1):
            raise ProtocolError('Missing or stacked Android mount: ' + target)
        return records[0] if records else None

    run = unique('/run', required=True)
    if run['fstype'] != 'tmpfs' or run['root'] != '/':
        raise ProtocolError('Android report workspace is not a fresh tmpfs')
    data, cache, system = unique('/data'), unique('/cache'), unique('/system')
    for target, record in [('/data', data), ('/cache', cache)]:
        if record and (record['fstype'] != 'tmpfs' or record['root'] != '/'):
            raise ProtocolError('Android ' + target + ' must be a fresh tmpfs')
    if system and not (data and cache):
        raise ProtocolError('Read-only Android system requires RAM data and cache')

    virtual_targets = {
        'rootfs': {'/'}, 'proc': {'/proc'}, 'sysfs': {'/sys'},
        'devtmpfs': {'/dev'}, 'devpts': {'/dev/pts'},
        'tmpfs': {'/dev', '/run', '/tmp', '/data', '/cache', '/mnt/asec', '/mnt/obb',
                  '/mnt/fuse', '/sys/fs/cgroup', '/system/etc/wifi',
                  '/system/vendor/firmware', '/system/lib/modules'},
        'debugfs': {'/sys/kernel/debug'},
        'pstore': {'/sys/fs/pstore'},
        'cgroup': {'/acct', '/dev/cpuctl', '/sys/fs/cgroup/memory'},
    }
    overlays = {'/system/lib/hw': '/xoom-hw', '/system/lib/egl': '/xoom-egl'}
    seen_overlays = []
    fuse = []
    remaining = list(info)
    for fields in mounts:
        source, target, fstype, options = fields[:4]
        record = next(record for record in remaining
                      if (record['source'], record['target'], record['fstype']) == (source, target, fstype))
        remaining.remove(record)
        opts = set(options.split(','))
        if any('\\' in item for item in (source, target, record['root'])):
            raise ProtocolError('Escaped paths are outside the fixed Android mount policy')
        if target == '/system':
            if (source not in ('/dev/mmcblk0p8', '/dev/block/mmcblk0p8') or fstype != 'ext4'
                    or not {'ro', 'nosuid', 'nodev'} <= opts or 'rw' in opts
                    or not {'ro', 'nosuid', 'nodev'} <= record['options']
                    or 'rw' in record['options'] or 'rw' in record['super_options']
                    or 'ro' not in record['super_options'] or record['root'] != '/'
                    or not {'noload', 'norecovery'} & opts
                    or not {'noload', 'norecovery'} & record['super_options']):
                raise ProtocolError('Android system must be fixed p8 ext4 read-only with journal replay disabled')
        elif target in overlays:
            if (not system or fstype != 'tmpfs' or record['device'] != run['device']
                    or record['root'] != overlays[target] or not {'ro', 'nosuid', 'nodev'} <= opts or 'rw' in opts
                    or not {'ro', 'nosuid', 'nodev'} <= record['options'] or 'rw' in record['options']):
                raise ProtocolError('Android graphics overlay is not a read-only bind from the RAM workspace')
            unique(target, required=True)
            seen_overlays.append(target)
        elif fstype == 'pstore':
            if (target != '/sys/fs/pstore' or 'ro' not in opts or 'rw' in opts
                    or 'ro' not in record['options'] or 'rw' in record['options']
                    or 'ro' not in record['super_options'] or 'rw' in record['super_options']
                    or record['root'] != '/'):
                raise ProtocolError('Android pstore mount must be read-only at the fixed path')
            unique(target, required=True)
        elif fstype in ('fuse', 'fuse.sdcard'):
            if (not system or not data or source != '/dev/fuse'
                    or not (target in ('/mnt/shell/emulated', '/storage/emulated')
                            or re.fullmatch(r'/storage/emulated/[0-9]+', target))):
                raise ProtocolError('Unexpected Android FUSE mount')
            fuse.append(record)
        elif fstype not in virtual_targets or target not in virtual_targets[fstype]:
            raise ProtocolError('Unexpected filesystem or mount path in Android read-only report')
        elif source.startswith('/dev/'):
            # None of the allowed virtual mounts should name a block/device source.
            raise ProtocolError('Unexpected device source for Android virtual filesystem')

    if fuse:
        primary = unique('/mnt/shell/emulated', required=True)
        if (primary['fstype'] not in ('fuse', 'fuse.sdcard') or primary['root'] != '/'
                or re.findall(r'^XOOM_ANDROID44_SDCARD_RAM_SOURCE (.*)$', policy, re.M) != ['verified']
                or any(item['device'] != primary['device'] for item in fuse)):
            raise ProtocolError('Android FUSE mount lacks the fixed RAM-backed sdcard process evidence')

    stages = _section(text, 'XOOM_ANDROID44_STAGES_BEGIN', 'XOOM_ANDROID44_STAGES_END')
    exec_attempted = 'XOOM_ANDROID44_STAGE exec_original_android_init' in stages.splitlines()
    if exec_attempted and (not system or set(seen_overlays) != set(overlays)):
        raise ProtocolError('Android init execution requires read-only system and both RAM graphics overlays')
    return {'storage_mode': 'android44-readonly', 'android_filesystems_mounted': bool(system),
            'kernel_release': releases[0],
            'ram_data_mounted': bool(data), 'ram_cache_mounted': bool(cache),
            'readonly_graphics_overlays': sorted(seen_overlays),
            'android_init_exec_attempted': exec_attempted,
            'all_emmc_readonly_flags': True}


def storage_result(payload, expected, disk_sectors=None, storage_mode='virtual-only'):
    if storage_mode not in ('virtual-only', 'android44-readonly'):
        raise ProtocolError('Unknown storage-report mode')
    if storage_mode == 'android44-readonly':
        if disk_sectors not in (None, 62521344):
            raise ProtocolError('Android44 profile requires the verified Wingray disk capacity reference')
        disk_sectors = 62521344
    text = payload.decode('utf-8', errors='replace')
    mount_lines = _section(text, 'XOOM_MOUNTS_BEGIN', 'XOOM_MOUNTS_END').splitlines()
    mounts = [line.split() for line in mount_lines]
    if any(len(fields) != 6 for fields in mounts):
        raise ProtocolError('Malformed mount-state evidence')
    virtual = {'rootfs', 'proc', 'sysfs', 'devtmpfs', 'tmpfs', 'devpts', 'debugfs', 'pstore'}
    android = {'storage_mode': 'virtual-only', 'android_filesystems_mounted': False}
    if storage_mode == 'android44-readonly':
        android = _android44_mount_policy(text, mounts)
    else:
        for fields in mounts:
            if fields[2] not in virtual:
                raise ProtocolError('Unexpected nonvirtual mount in diagnostic report')
    actual = {}
    for name, start, size in re.findall(r'^XOOM_PART (mmcblk0p[0-9]+) ([0-9]+) ([0-9]+)$', text, re.M):
        if name in actual:
            raise ProtocolError('Duplicate actual partition geometry')
        actual[name] = (int(start), int(size))
    disks = re.findall(r'^XOOM_DISK mmcblk0 ([0-9]+) ([01])$', text, re.M)
    if len(disks) > 1:
        raise ProtocolError('Duplicate disk geometry')
    result = {'state': 'not_discovered', **android,
              'actual': actual, 'missing': sorted(set(expected)-set(actual))}
    if not disks:
        if storage_mode == 'android44-readonly':
            raise ProtocolError('Android mode lacks the disk geometry and read-only snapshot')
        return result
    sectors, ro = map(int, disks[0])
    if storage_mode == 'android44-readonly' and ro != 1:
        raise ProtocolError('Android disk read-only evidence contradicts the Android policy section')
    result.update(disk_sectors=sectors, disk_read_only=bool(ro))
    if disk_sectors is not None and sectors != disk_sectors:
        result['state'] = 'disk_capacity_mismatch'
        return result
    if set(actual) != set(expected):
        result['state'] = 'partition_set_mismatch'
        return result
    extents = sorted(actual.values())
    if any(start < 0 or size <= 0 or start + size > sectors for start, size in extents):
        raise ProtocolError('Actual geometry is out of disk bounds')
    if any(a + size > b for (a, size), (b, _) in zip(extents, extents[1:])):
        raise ProtocolError('Actual partitions overlap')
    result['state'] = 'geometry_matches_reference' if actual == expected else 'geometry_mismatch'
    result['mismatches'] = {name: {'expected': expected[name], 'actual': actual[name]}
                            for name in expected if expected[name] != actual[name]}
    return result
