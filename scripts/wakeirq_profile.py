"""Fail closed on wake IRQ diagnostic scope; this is NOT a suspend profile."""
from pm_preparation_profile import blocked_pm
from pathlib import Path
from display_power_profile import resolved
from legacy_resources import parse_dtb

def validate_wakeirq_artifacts(directory, require_dc=None):
    p = Path(directory)
    cfg = (p / 'kernel.config').read_text()
    dc_test = 'CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y\n' in cfg
    if require_dc is not None:
        assert dc_test == require_dc, 'DC resume test config mismatch'
    for name in ('MFD_CPCAP_WINGRAY_IRQ_TEST',
                 'FB_TEGRA_WINGRAY_DISPLAY_PM', 'MFD_CPCAP', 'SMP', 'CACHE_L2X0'):
        assert 'CONFIG_' + name + '=y\n' in cfg, name
    if dc_test:
        assert 'CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y\n' in cfg
    blocked_pm(cfg)
    for name in ('PM', 'PM_SLEEP', 'SUSPEND', 'PM_AUTOSLEEP', 'CPU_FREQ', 'REGULATOR_CPCAP'):
        if name in ('PM','PM_SLEEP','SUSPEND') and blocked_pm(cfg):
            continue
        assert 'CONFIG_' + name + '=y\n' not in cfg, name
    assert any('CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="'+name+'"\n' in cfg for name in
               ('tegra20-motorola-wingray-android44-wakeirq', 'tegra20-motorola-wingray-android44-wakeirqtrace', 'tegra20-motorola-wingray-android44-wakeirqecc', 'tegra20-motorola-wingray-android44-lp2', 'tegra20-motorola-wingray-android44-persistent', 'tegra20-motorola-wingray-android44-persistent-inspect', 'tegra20-motorola-wingray-android44-persistent-write-test'))
    before = parse_dtb((p / 'tegra20-motorola-wingray-android44-displaypm.dtb').read_bytes())
    after = parse_dtb((p / 'tegra20-motorola-wingray-android44-wakeirq.dtb').read_bytes())
    assert set(before) == set(after)
    pmic = '/spi@7000d600/pmic@0'
    for node in before:
        a, b = resolved(before, node), resolved(after, node)
        if node == pmic:
            assert a.pop('interrupt-parent') == ('/interrupt-controller@50041000',)
            assert b.pop('interrupt-parent') == ('/interrupt-controller@60004000',)
            assert b.pop('motorola,wingray-on-irq-test') == b''
        assert a == b, node
