#!/usr/bin/env python3
"""Compile the actual read-only Tegra GPIO snapshot with controlled registers."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
src=(root/'sources/kernel-donor/drivers/gpio/gpio-tegra.c').read_text()
start=src.index('static void tegra_gpio_trace_wingray_usb(void)');opening=src.index('{',start);end=opening+1;depth=1
while depth:depth+=(src[end]=='{')-(src[end]=='}');end+=1
function=src[start:end]
macros=src[src.index('#define GPIO_BANK'):src.index('#define GPIO_MSK_CNF')]
binding=str(root/'sources/kernel-donor/include/dt-bindings/gpio/tegra-gpio.h')
fixture=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
static unsigned tegra_gpio_bank_stride=0x80;
struct gpio_chip { int unused; };
static struct gpio_chip tegra_gpio_chip;
static unsigned registers[1024],state,trace_calls,reads;
static bool wingray;
static unsigned owners;
static bool of_machine_is_compatible(const char *name) { assert(!strcmp(name,"motorola,wingray"));return wingray; }
static unsigned tegra_gpio_readl(unsigned reg) { assert(reg<sizeof(registers));++reads;return registers[reg/4]; }
static const char *gpiochip_is_requested(struct gpio_chip *chip,unsigned gpio) {
 assert(chip==&tegra_gpio_chip);
 if(gpio==172)return owners&1?"wingray-usb-data-enable":NULL;
 assert(gpio==21);return owners&2?"wingray-usb-forceon-n":"wrong-owner";
}
static void wingray_boottrace_gpio_state(unsigned value) { state=value;++trace_calls; }
'''
main=r'''
int main(void) {
 for(unsigned flags=0;flags<256;++flags) {
  memset(registers,0,sizeof(registers));owners=0;trace_calls=reads=0;wingray=true;
  for(unsigned i=0;i<2;++i) {
   unsigned gpio=i?21:172,nibble=(flags>>(i*4))&15;
   if(nibble&1)registers[GPIO_CNF(gpio)/4]|=1U<<GPIO_BIT(gpio);
   if(nibble&2)registers[GPIO_OE(gpio)/4]|=1U<<GPIO_BIT(gpio);
   if(nibble&4)registers[GPIO_OUT(gpio)/4]|=1U<<GPIO_BIT(gpio);
   if(nibble&8)owners|=1U<<i;
  }
  tegra_gpio_trace_wingray_usb();assert(trace_calls==1 && state==flags && reads==6);
 }
 wingray=false;trace_calls=reads=0;tegra_gpio_trace_wingray_usb();assert(trace_calls==0 && reads==0);
 puts("PASS 256 actual-source GPIO CNF/OE/OUT/owner combinations and non-Wingray exclusion; no register writes.");
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-gpio-snapshot-') as temp:
 p=Path(temp);(p/'test.c').write_text(fixture+macros+'\n#include "'+binding+'"\n'+function+main)
 subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror','-O2','-I',str(root/'sources/kernel-donor/include'),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
