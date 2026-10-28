"""Offline ownership and compatibility gates for the combined Motorola GPU profile."""
from pathlib import Path
import struct,hashlib
from legacy_resources import parse_dtb
from retained_console_profile import selected_retained_dt

def validate_artifacts(directory, *, require_framebuffer_translation=False):
 p=Path(directory)
 config=(p/'kernel.config').read_text()
 corrected='CONFIG_MOTOROLA_XOOM_SMP_TRACE_COOKIE=0x584d0060\n' in config
 name='tegra20-motorola-wingray-android44-gpu-fbmap' if corrected else 'tegra20-motorola-wingray-android44-gpu'
 bluetooth='CONFIG_RFKILL_WINGRAY_BT=y\n' in config
 battery='CONFIG_BATTERY_WINGRAY_MONITOR=y\n' in config
 displaypm='CONFIG_FB_TEGRA_WINGRAY_DISPLAY_PM=y\n' in config
 wakeirq='CONFIG_MFD_CPCAP_WINGRAY_IRQ_TEST=y\n' in config
 retained=selected_retained_dt(config)
 selected=retained if retained else 'tegra20-motorola-wingray-android44-wakeirq' if wakeirq else 'tegra20-motorola-wingray-android44-displaypm' if displaypm else 'tegra20-motorola-wingray-android44-battery' if battery else 'tegra20-motorola-wingray-android44-bluetooth' if bluetooth else name
 assert 'CONFIG_BUILD_ARM_APPENDED_DTB_IMAGE_NAMES="'+selected+'"\n' in config
 if bluetooth:
  from bluetooth_profile import validate_bluetooth_artifacts
  validate_bluetooth_artifacts(p)
 if battery:
  from battery_profile import validate_battery_artifacts
  validate_battery_artifacts(p)
 if displaypm:
  from display_power_profile import validate_display_power_artifacts
  validate_display_power_artifacts(p)
 if wakeirq:
  from wakeirq_profile import validate_wakeirq_artifacts
  validate_wakeirq_artifacts(p, require_dc='CONFIG_FB_TEGRA_WINGRAY_DC_RESUME_TEST=y\n' in config)
 if retained:
  from retained_console_profile import validate_retained_console_artifacts
  validate_retained_console_artifacts(p)
 if require_framebuffer_translation:assert corrected,'Known failed image59 has no fbmem bus translation'
 a=parse_dtb((p/'tegra20-motorola-wingray-gpu-test.dtb').read_bytes());b=parse_dtb((p/(name+'.dtb')).read_bytes())
 root='/host1x@50000000/dc@54200000'
 # DTC may renumber phandles when the DC gains a supply reference. Resolve
 # only schema-defined handle positions; preserve every GPIO/IRQ argument.
 def canonical(tree,n):
  handles={struct.unpack('>I',v['phandle'])[0]:path for path,v in tree.items() if 'phandle' in v}
  result={}
  for key,value in tree[n].items():
   if key in ('phandle','linux,phandle'):continue
   if key not in ('interrupt-parent','panel-supply','power-supply','pinctrl-0','dmas','gpio-ranges','interrupt-map'):
    result[key]=value;continue
   values=list(struct.unpack('>'+str(len(value)//4)+'I',value));out=[];i=0
   while i<len(values):
    if key=='interrupt-map':
     child=struct.unpack('>I',tree[n]['#address-cells'])[0]+struct.unpack('>I',tree[n]['#interrupt-cells'])[0]
     out.extend(values[i:i+child]);i+=child
    target=handles[values[i]];out.append(target);i+=1
    if key=='dmas':count=struct.unpack('>I',tree[target]['#dma-cells'])[0]
    elif key=='gpio-ranges':count=3
    elif key=='interrupt-map':
     count=struct.unpack('>I',tree[target].get('#address-cells',b'\0'*4))[0]+struct.unpack('>I',tree[target]['#interrupt-cells'])[0]
    else:count=0
    out.extend(values[i:i+count]);i+=count
   assert i==len(values),key
   result[key]=tuple(out)
  return result
 for n,props in a.items():
  if n=='/':
   assert {k:v for k,v in canonical(a,n).items() if k!='model'}=={k:v for k,v in canonical(b,n).items() if k!='model'}
  elif n=='/host1x@50000000' and corrected:
   old=canonical(a,n);new=canonical(b,n)
   assert {k:v for k,v in old.items() if k!='ranges'}=={k:v for k,v in new.items() if k!='ranges'}
   assert old['ranges']==struct.pack('>3I',0x54000000,0x54000000,0x04000000)
   assert new['ranges']==old['ranges']+struct.pack('>3I',0x2e800000,0x2e800000,0x00800000)
  elif not (n==root or n.startswith(root+'/')):assert canonical(a,n)==canonical(b,n),n
 assert set(b)-set(a)=={root+'/rgb/display',root+'/rgb/display/display-timings',root+'/rgb/display/display-timings/timing0'}
 dc=b[root];u=lambda n:struct.unpack('>'+str(len(n)//4)+'I',n)
 assert dc['status']==b'okay\0' and u(dc['reg'])==(0x54200000,0x40000,0x2e800000,0x800000)
 assert dc['reg-names']==b'regs\0fbmem\0' and dc['interrupt-names']==b'irq\0'
 assert set(dc)==set(a[root])|{'reg-names','interrupt-names','pnl-vdd-supply'}
 for key,value in a[root].items():
  if key not in ('reg','status'):assert value==dc[key],key
 assert dc['pnl-vdd-supply']==b['/i2c@7000c000/touchscreen@5b']['panel-supply']

 assert dc['clock-names']==b'dc\0parent\0' and dc['clocks']==a[root]['clocks']
 assert u(dc['assigned-clock-rates'])==(598000000,)
 assert b['/panel']['status']==b'disabled\0' # no competing DRM panel client
 assert 'motorola,xoom-firstboot-ro' in b['/sdhci@c8000600']
 mode=b[root+'/rgb/display'];timing=b[root+'/rgb/display/display-timings/timing0']
 for n,v in {'motorola,h-ref-to-sync':11,'motorola,v-ref-to-sync':1,'depth':24,'fb-xres':1280,'fb-yres':800,'fb-bpp':32,'lvds-to-bl':200}.items():assert u(mode[n])==(v,),n
 for n,v in {'clock-frequency':66400000,'hactive':1280,'vactive':800,'hfront-porch':45,'hsync-len':26,'hback-porch':12,'vfront-porch':3,'vsync-len':6,'vback-porch':3}.items():assert u(timing[n])==(v,),n
 s=(p/'kernel.config').read_text()
 for n in ['SMP','CACHE_L2X0','FB_TEGRA_WINGRAY_LEGACY','TEGRA_GRHOST_WINGRAY_GPU_TEST','ANDROID_BINDER_IPC_32BIT','ANDROID_LOGGER','MOTOROLA_XOOM_BIGPART','TOUCHSCREEN_ATMEL_MXT']:
  assert 'CONFIG_'+n+'=y\n' in s,n
 for n in ['DRM','TEGRA_HOST1X','TEGRA20_MC','CPU_FREQ','SUSPEND','MACH_SAMSUNG_P4WIFI','FB_TEGRA_CMC623']:
  assert 'CONFIG_'+n+'=y\n' not in s,n
