"""Verify the opt-in ramoops binding without expanding reserved RAM."""
from pm_preparation_profile import blocked_pm
from pathlib import Path
from display_power_profile import resolved
from legacy_resources import parse_dtb

TRACE_DT = 'tegra20-motorola-wingray-android44-wakeirqtrace'
ECC_DT = 'tegra20-motorola-wingray-android44-wakeirqecc'

def selected_retained_dt(config):
    for name in (TRACE_DT, ECC_DT):
        if 'CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="' + name + '"\n' in config:
            return name
    return None

def validate_ecc_tree(before, after):
    """ECC may change the log format, never board wiring or reservations."""
    import struct
    assert set(before) == set(after)
    for node in before:
        a, b = resolved(before, node), resolved(after, node)
        if node == '/':
            assert b.pop('motorola,wingray-pstore-ecc-test') == b''
        if node == '/ramoops@1ff00000':
            assert b.pop('ecc-size') == struct.pack('>I', 16)
        assert a == b, node

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
            # 4.4's ramoops_parse_dt_size() uses of_property_read_u64(),
            # so the trace profile must move the inherited one-cell sizes to
            # /bits/ 64.  The values themselves are unchanged.
            for name, value in (('record-size', 0x20000),
                                ('console-size', 0x80000),
                                ('pmsg-size', 0x20000)):
                assert a.pop(name) == struct.pack('>I', value), name
                assert b.pop(name) == struct.pack('>Q', value), name
        assert a == b, node
    props = resolved(after, region)
    assert props == {'reg': struct.pack('>II', 0x1ff00000, 0x100000), 'no-map': b''}
    intervals = ranges(after)
    assert all(left[1] <= right[0] for left, right in zip(intervals, intervals[1:])), 'Overlapping reservations'
    assert merged(ranges(before)) == merged(intervals), 'Changed reserved RAM union'
    # Driver's record/console/pmsg subregions must exactly fit, not underflow.
    u64 = lambda name: struct.unpack('>Q', after[consumer][name])[0]
    record, console, pmsg = u64('record-size'), u64('console-size'), u64('pmsg-size')
    assert (record, console, pmsg) == (0x20000, 0x80000, 0x20000)
    assert (0x100000 - console - pmsg) // record == 3

def validate_retained_console_artifacts(directory):
    p = Path(directory)
    cfg = (p / 'kernel.config').read_text()
    for option in ('PSTORE', 'PSTORE_CONSOLE', 'PSTORE_RAM', 'MFD_CPCAP_WINGRAY_IRQ_TEST'):
        assert 'CONFIG_' + option + '=y\n' in cfg, option
    dc_trace = 'CONFIG_FB_TEGRA_WINGRAY_DC_TRACE_TEST=y\n' in cfg
    blocked_pm(cfg)
    for option in ('PM', 'SUSPEND', 'CPU_FREQ', 'REGULATOR_CPCAP'):
        if option in ('PM','PM_SLEEP','SUSPEND') and blocked_pm(cfg):
            continue
        assert 'CONFIG_' + option + '=y\n' not in cfg, option
    selected = selected_retained_dt(cfg)
    assert selected, 'Not an isolated retained-console profile'
    if dc_trace:
        assert selected == ECC_DT
        assert 'CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y\n' in cfg
    else:
        assert 'CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y\n' not in cfg
    before = parse_dtb((p / 'tegra20-motorola-wingray-android44-wakeirq.dtb').read_bytes())
    after = parse_dtb((p / (TRACE_DT + '.dtb')).read_bytes())
    validate_trees(before, after)
    if selected == ECC_DT:
        for name in ('REED_SOLOMON', 'REED_SOLOMON_ENC8', 'REED_SOLOMON_DEC8'):
            assert 'CONFIG_' + name + '=y\n' in cfg, name
        validate_ecc_tree(after, parse_dtb((p / (ECC_DT + '.dtb')).read_bytes()))
