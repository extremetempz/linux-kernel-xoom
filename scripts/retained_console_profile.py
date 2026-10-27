"""Verify the opt-in ramoops binding without expanding reserved RAM."""
from pathlib import Path
from display_power_profile import resolved
from legacy_resources import parse_dtb

def ranges(tree):
    import struct
    result = []
    for node, props in tree.items():
        if node.startswith('/reserved-memory/') and 'reg' in props:
            values = struct.unpack('>' + 'I' * (len(props['reg']) // 4), props['reg'])
            assert len(values) == 2
            start, size = values
            assert size > 0 and start + size <= 0x40000000
            result.append((start, start + size))
    return sorted(result)

def merged(intervals):
    result = []
    for start, end in intervals:
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result

def validate_trees(before, after):
    import struct
    region = '/reserved-memory/ramoops@1ff00000'
    legacy = '/reserved-memory/legacy-console@1fe00000'
    consumer = '/ramoops@1ff00000'
    assert set(after) - set(before) == {region}
    assert set(before) - set(after) == set()
    for node in before:
        a, b = resolved(before, node), resolved(after, node)
        if node == '/':
            assert b.pop('motorola,wingray-pstore-test') == b''
        if node == legacy:
            assert a.pop('reg') == struct.pack('>II', 0x1fe00000, 0x200000)
            assert b.pop('reg') == struct.pack('>II', 0x1fe00000, 0x100000)
        if node == consumer:
            assert b.pop('memory-region') == (region,)
        assert a == b, node
    props = resolved(after, region)
    assert props == {'reg': struct.pack('>II', 0x1ff00000, 0x100000), 'no-map': b''}
    intervals = ranges(after)
    assert all(left[1] <= right[0] for left, right in zip(intervals, intervals[1:])), 'Overlapping reservations'
    assert merged(ranges(before)) == merged(intervals), 'Changed reserved RAM union'
    # Driver's record/console/pmsg subregions must exactly fit, not underflow.
    u32 = lambda name: struct.unpack('>I', after[consumer][name])[0]
    assert (u32('record-size'), u32('console-size'), u32('pmsg-size')) == (0x20000, 0x80000, 0x20000)
    assert (0x100000 - u32('console-size') - u32('pmsg-size')) // u32('record-size') == 3

def validate_retained_console_artifacts(directory):
    p = Path(directory)
    cfg = (p / 'kernel.config').read_text()
    for option in ('PSTORE', 'PSTORE_CONSOLE', 'PSTORE_RAM', 'MFD_CPCAP_WINGRAY_IRQ_TEST'):
        assert 'CONFIG_' + option + '=y\n' in cfg, option
    for option in ('FB_TEGRA_WINGRAY_DC_RESUME_TEST', 'PM', 'SUSPEND', 'CPU_FREQ', 'REGULATOR_CPCAP'):
        assert 'CONFIG_' + option + '=y\n' not in cfg, option
    assert 'CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="tegra20-motorola-wingray-android44-wakeirqtrace"\n' in cfg
    before = parse_dtb((p / 'tegra20-motorola-wingray-android44-wakeirq.dtb').read_bytes())
    after = parse_dtb((p / 'tegra20-motorola-wingray-android44-wakeirqtrace.dtb').read_bytes())
    validate_trees(before, after)
