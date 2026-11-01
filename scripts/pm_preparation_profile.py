"""Permit PM in an Android test image only with the mandatory entry block."""
def blocked_pm(config):
    yes=lambda key: 'CONFIG_'+key+'=y\n' in config
    if not (yes('MOTOROLA_WINGRAY_PM_PREPARE') or yes('MFD_CPCAP_WINGRAY_WAKE_ARM_TEST')):
        return False
    for key in ('MOTOROLA_WINGRAY_PM_PREPARE','MFD_CPCAP_WINGRAY_WAKE_ARM_TEST',
                'MFD_CPCAP_WINGRAY_IRQ_TEST','PM','PM_SLEEP','SUSPEND','SUSPEND_FREEZER',
                'PM_DEBUG','PM_SLEEP_DEBUG','HOTPLUG_CPU','SMP','PSTORE_RAM','PSTORE_CONSOLE',
                'TEGRA_GRHOST_WINGRAY_GPU_TEST','FB_TEGRA_WINGRAY_LEGACY'):
        assert yes(key), 'Blocked PM profile missing '+key
    if yes('MOTOROLA_WINGRAY_DEVICEPM_TEST'):
        assert yes('MOTOROLA_WINGRAY_FREEZER_TEST') and yes('MFD_CPCAP'), 'Device test needs freezer and built-in CPCAP'
    if yes('MOTOROLA_WINGRAY_DPM_TEST'):
        assert yes('MOTOROLA_WINGRAY_DEVICEPM_TEST'), 'DPM test needs selected CPCAP callback path'
    for key in ('PM_AUTOSLEEP','PM_WAKELOCKS','PM_TEST_SUSPEND','HIBERNATION',
                'DPM_WATCHDOG','CPU_IDLE','CPU_FREQ','REGULATOR_CPCAP',
                'FB_TEGRA_WINGRAY_DC_RESUME_TEST','FB_TEGRA_WINGRAY_DC_TRACE_TEST'):
        assert not yes(key), 'Blocked PM profile forbids '+key
    dtbs=('tegra20-motorola-wingray-android44-wakeirqecc','tegra20-motorola-wingray-android44-lp2','tegra20-motorola-wingray-android44-persistent','tegra20-motorola-wingray-android44-persistent-inspect','tegra20-motorola-wingray-android44-persistent-write-test')
    assert any('CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="'+d+'"\n' in config for d in dtbs)
    return True
