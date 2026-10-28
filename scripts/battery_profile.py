"""Preserve every existing Bluetooth/GPU/CPCAP node in the opt-in monitor DT."""
from pm_preparation_profile import blocked_pm
from pathlib import Path
from legacy_resources import parse_dtb
from bluetooth_profile import canonical, cells

def validate_trees(base, monitor):
    added={'/wingray_battery_monitor','/onewire@7000c600',
           '/pinmux@70000014/battery-owr-pins','/pinmux@70000014/battery-owr-pins/owc'}
    assert set(monitor)-set(base)==added
    assert not set(base)-set(monitor)
    for node in base:
        assert canonical(base,node)==canonical(monitor,node),node
    p=monitor['/wingray_battery_monitor']
    assert p['compatible']==b'motorola,wingray-p3-battery-monitor\0'
    for name,num in [('stat1',173),('stat2',25),('detect',174)]:
        assert canonical(monitor,'/wingray_battery_monitor')[name+'-gpios']==('/gpio@6000d000',num,0)
    n=monitor['/onewire@7000c600']
    assert cells(n['reg'])==(0x7000c600,0x50)
    assert cells(n['interrupts'])==(0,30,4)
    assert canonical(monitor,'/onewire@7000c600')['clocks']==('/clock@60006000',71)
    assert canonical(monitor,'/onewire@7000c600')['resets']==('/clock@60006000',71)
    assert canonical(monitor,'/pinmux@70000014/battery-owr-pins/owc')=={
        'nvidia,pins':b'owc\0','nvidia,function':b'owr\0',
        'nvidia,pull':(2).to_bytes(4,'big'),'nvidia,tristate':bytes(4)}

def validate_battery_artifacts(directory):
    p=Path(directory);config=(p/'kernel.config').read_text()
    for name in ('POWER_SUPPLY','W1','W1_MASTER_TEGRA_WINGRAY','W1_SLAVE_DS2781','BATTERY_WINGRAY_MONITOR'):
        assert 'CONFIG_'+name+'=y\n' in config,name
    blocked_pm(config)
    for name in ('BATTERY_DS2781','BATTERY_SBS','REGULATOR_CPCAP','CPU_FREQ','SUSPEND','SOUND'):
        if name in ('PM','PM_SLEEP','SUSPEND') and blocked_pm(config):
            continue
        assert 'CONFIG_'+name+'=y\n' not in config,name
    validate_trees(parse_dtb((p/'tegra20-motorola-wingray-android44-bluetooth.dtb').read_bytes()),
                   parse_dtb((p/'tegra20-motorola-wingray-android44-battery.dtb').read_bytes()))
