#!/usr/bin/env python3
"""Source-order gate for masking the CPCAP parent IRQ across SPI sleep."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'sources/kernel-donor/drivers/mfd/motorola-cpcap.c'
s=p.read_text()
def fn(name):
    a=s.index('static int '+name)
    b=s.index('\n}\n',a)+3
    return s[a:b]
sus=fn('cpcap_wingray_pm_suspend'); res=fn('cpcap_wingray_pm_resume')
assert 'cpcap_wingray_set_wake_arm(cpcap, true)' in sus
assert sus.index('cpcap_wingray_set_wake_arm(cpcap, true)') < sus.index('disable_irq(cpcap->spi->irq)')
assert 'irq_masked = true' in sus
assert res.index('enable_irq(cpcap->spi->irq)') < res.index('cpcap_wingray_set_wake_arm(cpcap, false)')
assert 'irq_masked = false' in res
assert 'WG_PM94_CPCAP_SUSPEND' in sus and 'WG_PM94_CPCAP_RESUME' in res
# The wake arm must not be released before the IRQ is usable again.
assert res.index('enable_irq') < res.index('set_wake_arm(cpcap, false)')
print('PASS CPCAP IRQ mask/unmask ordering and wake-arm lifetime gates')
