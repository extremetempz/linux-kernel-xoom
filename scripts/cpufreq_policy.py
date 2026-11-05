"""Only permit CPU_FREQ in the fixed-clock Wingray GPU profile."""
def cpufreq_gpu_ok(config):
    if 'CONFIG_CPU_FREQ=y\n' not in config:
        return False
    for key in ('ARM_TEGRA20_CPUFREQ', 'CPU_FREQ_DEFAULT_GOV_PERFORMANCE',
                'TEGRA_GRHOST_WINGRAY_GPU_TEST'):
        assert 'CONFIG_' + key + '=y\n' in config, key
    assert 'CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y\n' not in config
    return True
