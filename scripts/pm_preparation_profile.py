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
    for key in ('PM_AUTOSLEEP','PM_WAKELOCKS','PM_TEST_SUSPEND','HIBERNATION',
                'DPM_WATCHDOG','CPU_IDLE','CPU_FREQ','REGULATOR_CPCAP',
                'FB_TEGRA_WINGRAY_DC_RESUME_TEST','FB_TEGRA_WINGRAY_DC_TRACE_TEST'):
        assert not yes(key), 'Blocked PM profile forbids '+key
    assert 'CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="tegra20-motorola-wingray-android44-wakeirqecc"\n' in config
    return True
