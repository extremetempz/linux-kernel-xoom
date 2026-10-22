#!/usr/bin/env python3
"""Compile the actual isolated P3 touch DT and compare it to the booted control.

Use --dtc /path/to/kernel-build/out/scripts/dtc/dtc when dtc is not installed.
Optional --config checks the final expanded kernel config, not just a defconfig.
No device, I2C transaction, controller write or firmware file is involved.
"""
import argparse
from copy import deepcopy
from pathlib import Path
import re
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / 'sources/kernel-donor'
DTS = TREE / 'arch/arm/boot/dts'
CONTROL = 'tegra20-motorola-wingray-android44'
TOUCH = CONTROL + '-touch'
MUX = '/pinmux@70000014/panelbus-mux/'
NODE = '/i2c@7000c000/touchscreen@5b'
GROUPS = {
    'touch-wake': ('gmd', 'gmi', 2, 'TEGRA_PIN_GMI_CS1_N_PJ2'),
    'touch-reset': ('kbcd', 'sdio2', 2, 'TEGRA_PIN_KB_ROW4_PR4'),
    'touch-irq': ('uac', 'rsvd4', 0, 'TEGRA_PIN_PV2'),
}


def cells(value):
    return struct.unpack('>' + 'I' * (len(value) // 4), value)


def strings(value):
    return value.rstrip(b'\0').decode().split('\0')


def parse_dtb(data):
    magic, total, cursor, off_strings = struct.unpack_from('>4I', data)
    assert magic == 0xd00dfeed and total == len(data)
    nodes, stack = {}, []
    while True:
        token, = struct.unpack_from('>I', data, cursor)
        cursor += 4
        if token == 1:
            end = data.index(0, cursor)
            stack.append(data[cursor:end].decode())
            cursor = (end + 4) & ~3
            nodes['/'.join(stack) or '/'] = {}
        elif token == 2:
            stack.pop()
        elif token == 3:
            length, offset = struct.unpack_from('>II', data, cursor)
            cursor += 8
            start = off_strings + offset
            name = data[start:data.index(0, start)].decode()
            nodes['/'.join(stack) or '/'][name] = data[cursor:cursor + length]
            cursor = (cursor + length + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            return nodes
        else:
            raise AssertionError('Invalid DTB token')


def compile_dt(name, dtc):
    # CPP expands the same pinned GPIO and IRQ binding constants as Kbuild.
    source = subprocess.check_output([
        'cpp', '-nostdinc', '-undef', '-D__DTS__', '-x', 'assembler-with-cpp',
        '-I', str(TREE / 'include'), '-I', str(DTS), str(DTS / (name + '.dts')),
    ])
    result = subprocess.run([dtc, '-I', 'dts', '-O', 'dtb', '-o', '-'],
                            input=source, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=True)
    return parse_dtb(result.stdout)


def audit_touch(nodes, base):
    assert set(nodes) - set(base) == {NODE, *(MUX + x for x in GROUPS)}
    assert not set(base) - set(nodes)
    # The tested display, USB, MMC/read-only safety and all disabled devices
    # retain their exact compiled properties. Only the root description changes.
    def canonical(path, tree):
        # DTC assigns phandles in reference order. Adding a GPIO client can
        # renumber existing providers, so compare their target paths rather
        # than treating changed handle numbers as changed hardware wiring.
        providers = {cells(p['phandle'])[0]: n for n, p in tree.items()
                     if 'phandle' in p}
        props = dict(tree[path])
        for name in ['phandle', 'linux,phandle']:
            if name in props:
                assert providers[cells(props[name])[0]] == path
                props[name] = ('provider', path)
        for name in ['interrupt-parent', 'nvidia,phy', 'gpio']:
            if name in props:
                values = cells(props[name])
                props[name] = (providers[values[0]], *values[1:])
        if 'clocks' in props:
            values, cursor, clocks = cells(props['clocks']), 0, []
            while cursor < len(values):
                provider = providers[values[cursor]]
                count, = cells(tree[provider]['#clock-cells'])
                clocks.append((provider, *values[cursor + 1:cursor + 1 + count]))
                cursor += 1 + count
            assert cursor == len(values)
            props['clocks'] = tuple(clocks)
        return props

    for path in base:
        old, new = canonical(path, base), canonical(path, nodes)
        if path == '/':
            old.pop('model')
            new.pop('model')
        assert old == new, 'Unexpected control-profile change: ' + path
    touch = nodes[NODE]
    assert set(touch) == {'compatible', 'reg', 'interrupt-parent', 'interrupts',
                          'enable-gpios', 'reset-gpios', 'panel-supply'}
    assert strings(touch['compatible']) == ['motorola,wingray-maxtouch',
                                            'atmel,maxtouch']
    assert cells(touch['reg']) == (0x5b,)
    gpio = cells(nodes['/gpio@6000d000']['phandle'])[0]
    assert cells(touch['interrupt-parent']) == (gpio,)
    assert cells(touch['interrupts']) == (170, 8)  # PV2, IRQ_TYPE_LEVEL_LOW
    assert cells(touch['enable-gpios']) == (gpio, 74, 1)  # PJ2, active low
    assert cells(touch['reset-gpios']) == (gpio, 140, 1)  # PR4, active low
    assert touch['panel-supply'] == nodes['/panel-power']['phandle']
    assert touch['panel-supply'] == nodes['/panel']['power-supply']
    assert 'motorola,xoom-firstboot-ro' in nodes['/sdhci@c8000600']
    for node, (group, function, pull, _) in GROUPS.items():
        props = nodes[MUX + node]
        assert set(props) == {'nvidia,pins', 'nvidia,function', 'nvidia,tristate',
                              'nvidia,pull'}
        assert strings(props['nvidia,pins']) == [group]
        assert strings(props['nvidia,function']) == [function]
        assert cells(props['nvidia,tristate']) == (0,)
        assert cells(props['nvidia,pull']) == (pull,)


def audit_actual_pin_driver():
    driver = (TREE / 'drivers/pinctrl/pinctrl-tegra20.c').read_text()
    caps = {}
    for line in driver.splitlines():
        match = re.search(r'\bMUX_PG\(([^\n]+)\)', line)
        if not match:
            continue
        values = [x.strip() for x in match[1].split(',')]
        if len(values) == 11 and values[5].startswith(('0x', '-')):
            caps[values[0]] = values
    for group, function, _, pin in GROUPS.values():
        values = caps[group]
        assert function.upper() in values[1:5]
        assert int(values[5], 0) >= 0, group + ' has no tristate field'
        assert int(values[9], 0) >= 0, group + ' has no pull field'
        mapping = re.search(r'static const unsigned ' + group +
                            r'_pins\[\] = \{([^}]+)\}', driver)
        assert mapping and pin in mapping[1], 'Incorrect GPIO-to-group mapping'
    # The Motorola baseline independently identifies the P3 wiring, distinct
    # from P2's PZ2 alternative. Factory T9 range/orientation is read, not guessed
    # from the 1280x800 LCD or overwritten in the touch device tree.
    legacy = (ROOT / 'sources/kernel-baseline/arch/arm/mach-tegra/'
              'board-stingray-touch.c').read_text()
    for name, pin in [('RESET', 'PR4'), ('INT', 'PV2'), ('WAKE', 'PJ2')]:
        assert re.search('STINGRAY_TOUCH_' + name + r'_N_GPIO\s+TEGRA_GPIO_' + pin,
                         legacy)
    mxt = (TREE / 'drivers/input/touchscreen/atmel_mxt_ts.c').read_text()
    resolution = mxt.split('static int mxt_read_t9_resolution', 1)[1].split(
        '\nstatic ', 1)[0]
    for token in ['MXT_T9_RANGE', 'MXT_T9_ORIENT', 'MXT_T9_ORIENT_SWITCH',
                  'data->max_x = range.y', 'data->max_y = range.x']:
        assert token in resolution


def config_values(path):
    result = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_'):
            name, value = line.split('=', 1)
            result[name.removeprefix('CONFIG_')] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            result[line[9:-11]] = 'n'
    return result


def audit_config(path, expanded=False):
    config = config_values(path)
    for name in ['INPUT', 'INPUT_EVDEV', 'INPUT_TOUCHSCREEN',
                 'TOUCHSCREEN_ATMEL_MXT']:
        assert config[name] == 'y', name
    for name in ['TOUCHSCREEN_MXT1386', 'SAMSUNG_INPUT', 'INPUT_LEDS',
                 'INPUT_MOUSEDEV', 'INPUT_JOYDEV', 'INPUT_KEYBOARD', 'INPUT_MOUSE',
                 'INPUT_JOYSTICK', 'INPUT_TABLET', 'INPUT_MISC', 'SERIO',
                 'GAMEPORT', 'HID', 'USB_HID']:
        assert config.get(name, 'n') == 'n', name
    assert config['LOCALVERSION'] == '"-wingray-android44-touch"'
    assert config['BUILD_ARM_APPENDED_DTB_IMAGE_NAMES'] == '"' + TOUCH + '"'
    assert config['MOTOROLA_XOOM_BOOT_TRACE_COOKIE'] == '0x584d0020'
    original = config_values(TREE / 'arch/arm/configs/wingray_android44_defconfig')
    for name, value in original.items():
        if name not in ['INPUT', 'LOCALVERSION',
                        'BUILD_ARM_APPENDED_DTB_IMAGE_NAMES',
                        'MOTOROLA_XOOM_BOOT_TRACE_COOKIE']:
            # Kconfig omits unavailable disabled symbols from the expanded
            # .config (for example a Samsung-only machine option).
            assert config.get(name, 'n') == value, 'Control config changed: ' + name
    if expanded:
        assert config['FW_LOADER'] == 'y'
        allowed = {'INPUT', 'INPUT_EVDEV', 'INPUT_TOUCHSCREEN'}
        assert {n for n, v in config.items() if n.startswith('INPUT') and
                v in ('y', 'm')} == allowed
        assert {n for n, v in config.items() if n.startswith('TOUCHSCREEN_') and
                v in ('y', 'm')} == {'TOUCHSCREEN_ATMEL_MXT',
                                     'TOUCHSCREEN_PROPERTIES'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dtc', default=shutil.which('dtc'))
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    if not args.dtc:
        parser.error('--dtc must point to the built kernel DTC')
    audit_actual_pin_driver()
    audit_config(TREE / 'arch/arm/configs/wingray_android44_touch_defconfig')
    if args.config:
        audit_config(args.config, expanded=True)
    control, touch = [compile_dt(n, args.dtc) for n in (CONTROL, TOUCH)]
    assert NODE not in control
    audit_touch(touch, control)
    # Prove the acceptance gates reject P2 IRQ substitution, wrong GPIO
    # polarity, a different rail, and a broad peripheral DT inclusion.
    for property_name, bad in [('interrupts', struct.pack('>II', 202, 8)),
                               ('reset-gpios', struct.pack('>III',
                                cells(touch[NODE]['reset-gpios'])[0], 140, 0)),
                               ('panel-supply', struct.pack('>I', 0xffffffff))]:
        mutated = deepcopy(touch)
        mutated[NODE][property_name] = bad
        try:
            audit_touch(mutated, control)
        except AssertionError:
            pass
        else:
            raise AssertionError('Unsafe touch wiring was accepted')
    mutated = deepcopy(touch)
    mutated['/spi@7000d400/pmic@0'] = {'status': b'okay\0'}
    try:
        audit_touch(mutated, control)
    except AssertionError:
        pass
    else:
        raise AssertionError('Broad PMIC enablement was accepted')
    print('PASS: actual compiled P3 touch DT adds only one controller and three '
          'supported pin groups; control display/USB/read-only MMC unchanged.')


if __name__ == '__main__':
    main()
