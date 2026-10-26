"""Reject display-power experiments that alter tested board wiring or enable sleep."""
from pathlib import Path
from legacy_resources import parse_dtb
from bluetooth_profile import canonical, cells

def resolved(tree, node):
    result=canonical(tree,node)
    handles={cells(v["phandle"])[0]:n for n,v in tree.items() if "phandle" in v}
    for key in ("nvidia,panel","gpio-ranges","interrupt-map"):
        if key not in tree[node]:continue
        values=cells(tree[node][key]); out=[];i=0
        while i<len(values):
            if key=="interrupt-map":
                count=cells(tree[node]["#address-cells"])[0]+cells(tree[node]["#interrupt-cells"])[0]
                out.extend(values[i:i+count]);i+=count
            target=handles[values[i]];out.append(target);i+=1
            count=3 if key=="gpio-ranges" else (cells(tree[target].get("#address-cells",bytes(4)))[0]+cells(tree[target]["#interrupt-cells"])[0]) if key=="interrupt-map" else 0
            out.extend(values[i:i+count]);i+=count
        assert i==len(values)
        result[key]=tuple(out)
    return result


def validate_display_power_artifacts(directory):
    p=Path(directory);cfg=(p/'kernel.config').read_text()
    assert 'CONFIG_FB_TEGRA_WINGRAY_DISPLAY_PM=y\n' in cfg
    for option in ('PM','PM_SLEEP','SUSPEND','CPU_FREQ','PM_AUTOSLEEP','REGULATOR_CPCAP'):
        assert 'CONFIG_'+option+'=y\n' not in cfg,option
    a=parse_dtb((p/'tegra20-motorola-wingray-android44-battery.dtb').read_bytes())
    b=parse_dtb((p/'tegra20-motorola-wingray-android44-displaypm.dtb').read_bytes())
    assert set(a)==set(b)
    dc='/host1x@50000000/dc@54200000'
    for n in a:
        x,y=resolved(a,n),resolved(b,n)
        if n=='/':
            assert y.pop('motorola,wingray-display-pm-test')==b''
        if n==dc:
            assert y.pop('backlight')==('/i2c@7000c000/backlight@2c',)
        assert x==y,n
