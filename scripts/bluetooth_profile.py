"""Reject Bluetooth profiles that alter tested display, Wi-Fi or storage wiring."""
from pathlib import Path
import struct
from legacy_resources import parse_dtb

def cells(value):
    return struct.unpack('>'+'I'*(len(value)//4), value)

def canonical(tree, path):
    handles={cells(p['phandle'])[0]:n for n,p in tree.items() if 'phandle' in p}
    result={}
    kinds={'clocks':'#clock-cells','resets':'#reset-cells','dmas':'#dma-cells','phys':'#phy-cells'}
    for key,value in tree[path].items():
        if key in ('phandle','linux,phandle'):
            continue
        kind=kinds.get(key)
        if (key.endswith('-gpios') or key in ('gpio','gpios')) and 'gpio-hog' not in tree[path]:
            kind='#gpio-cells'
        single=key.endswith('-supply') or key in ('interrupt-parent','pinctrl-0','panel-supply','power-supply','mmc-pwrseq','nvidia,phy','backlight','memory-region')
        if kind or single:
            values=list(cells(value)); out=[]; i=0
            while i<len(values):
                target=handles[values[i]];out.append(target);i+=1
                count=cells(tree[target][kind])[0] if kind else 0
                out.extend(values[i:i+count]);i+=count
            result[key]=tuple(out)
        else:
            result[key]=value
    return result

def validate_trees(base, bt):
    power='/bluetooth-power';uart='/serial@70006200';pin='/pinmux@70000014/bluetooth-uart-pins'
    extras={power,pin,pin+'/uca',pin+'/ucb'}
    assert set(bt)-set(base)==extras, 'unexpected DT nodes'
    assert not set(base)-set(bt), 'removed baseline nodes'
    for n in base:
        a=canonical(base,n);b=canonical(bt,n)
        allowed={'model'} if n=='/' else {'serial2'} if n=='/aliases' else {'compatible','status','pinctrl-names','pinctrl-0'} if n==uart else set()
        assert {k:v for k,v in a.items() if k not in allowed}=={k:v for k,v in b.items() if k not in allowed}, n
    assert bt['/aliases']['serial2']==b'/serial@70006200\0'
    u=bt[uart]
    assert u['compatible']==b'nvidia,tegra20-hsuart\0' and u['status']==b'okay\0'
    assert canonical(bt,uart)['pinctrl-0']==(pin,)
    expected={'compatible':b'motorola,wingray-bcm4329-bt\0','vdd-supply':('/wlan-power',),
              'reset-gpios':('/gpio@6000d000',160,0),'shutdown-gpios':('/gpio@6000d000',71,0),
              'device-wake-gpios':('/gpio@6000d000',161,0),'host-wake-gpios':('/gpio@6000d000',166,0)}
    assert canonical(bt,power)==expected, 'Motorola-only power wiring'
    for group in ('uca','ucb'):
        assert canonical(bt,pin+'/'+group)=={'nvidia,pins':(group+'\0').encode(),'nvidia,function':b'uartc\0','nvidia,tristate':struct.pack('>I',0),'nvidia,pull':struct.pack('>I',2)}

def validate_bluetooth_artifacts(directory):
    p=Path(directory);s=(p/'kernel.config').read_text()
    for name in ('SERIAL_TEGRA','RFKILL','RFKILL_WINGRAY_BT','TEGRA20_APB_DMA','BROADCOM_WIFI'):
        assert 'CONFIG_'+name+'=y\n' in s,name
    assert '# CONFIG_BT is not set\n' in s, 'Android HAL owns HCI UART'
    validate_trees(parse_dtb((p/'tegra20-motorola-wingray-android44-gpu-fbmap.dtb').read_bytes()),
                   parse_dtb((p/'tegra20-motorola-wingray-android44-bluetooth.dtb').read_bytes()))
