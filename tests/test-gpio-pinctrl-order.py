#!/usr/bin/env python3
"""Reproduce one-shot GPIO hog loss using actual OF/request control flow.

DT lookup, provider registration and GPIO writes are controlled dependencies.
No kernel boot, hardware state or electrical operation is emulated.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
def block(path,prefix):
 text=(root/'sources/kernel-donor'/path).read_text();start=text.index(prefix);opening=text.index('{',start);end=opening+1;depth=1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
functions='\n'.join([
 block('drivers/pinctrl/pinctrl-tegra.c','static bool gpio_node_has_range('),
 block('drivers/pinctrl/core.c','int pinctrl_request_gpio('),
 block('drivers/gpio/gpio-tegra.c','static int tegra_gpio_request('),
 block('drivers/gpio/gpiolib.c','int gpiod_hog('),
 block('drivers/gpio/gpiolib-of.c','static int of_gpiochip_add_pin_range('),
 block('drivers/gpio/gpiolib-of.c','static void of_gpiochip_scan_gpios('),
 block('drivers/gpio/gpiolib-of.c','int of_gpiochip_add('),
])
fixture=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
#define EPROBE_DEFER 517
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define PTR_ERR(x) ((int)(intptr_t)(x))
#define IS_ERR(x) ((uintptr_t)(x) > (uintptr_t)-4096)
#define pr_err(...) ((void)0)
#define pr_info(...) ((void)0)
#define FLAG_IS_HOGGED 0
#define NULL_NODE ((struct device_node *)0)
struct device_node { const char *full_name; int line; struct device_node *next,*child; };
struct property { int unused; };
struct device { struct device_node *of_node; };
struct gpio_chip { struct device_node *of_node; struct device *dev; int of_gpio_n_cells; void *of_xlate; };
struct pinctrl_dev { int mutex; };
struct pinctrl_gpio_range { int unused; };
struct of_phandle_args { struct device_node *np; u32 args[3]; };
struct gpio_desc { int line; unsigned long flags; };
enum gpio_lookup_flags { GPIO_ACTIVE_HIGH = 0 };
enum gpiod_flags { GPIOD_OUT_HIGH = 3 };
static struct device_node gpio_node={"gpio",0,0,0},pin_node={"pinmux",0,0,0};
static struct pinctrl_dev provider;
static struct pinctrl_gpio_range range;
static struct property prop;
static struct gpio_desc descriptors[2]={{172,0},{21,0}};
static bool has_range,provider_ready,range_ready;
static int soc,hog_attempts,directions,range_adds,puts;
static int tegra_gpio_request(struct gpio_chip *,unsigned);
static struct device_node *of_find_compatible_node(void *a,void *b,const char *name) {
 (void)a;(void)b;
 return ((soc==20 && !strcmp(name,"nvidia,tegra20-gpio")) ||
         (soc==30 && !strcmp(name,"nvidia,tegra30-gpio"))) ? &gpio_node:NULL;
}
static struct property *of_find_property(struct device_node *n,const char *name,void *p) {
 (void)p; return n==&gpio_node && has_range && !strcmp(name,"gpio-ranges") ? &prop:NULL;
}
static void of_node_put(struct device_node *n) { assert(n==&gpio_node);++puts; }
static void of_node_get(struct device_node *n) { assert(n==&gpio_node); }
static int of_parse_phandle_with_fixed_args(struct device_node *n,const char *name,int cells,int i,struct of_phandle_args *out) {
 assert(n==&gpio_node && !strcmp(name,"gpio-ranges") && cells==3);
 if (!has_range || i) return -2;
 out->np=&pin_node;out->args[0]=out->args[1]=0;out->args[2]=224;return 0;
}
static struct pinctrl_dev *of_pinctrl_get(struct device_node *n) { assert(n==&pin_node);return provider_ready?&provider:NULL; }
static int of_property_read_string_index(struct device_node *n,const char *name,int i,const char **out) {
 (void)n;(void)name;(void)i;(void)out;assert(0);return -1;
}
static int gpiochip_add_pin_range(struct gpio_chip *chip,const char *name,unsigned a,unsigned b,unsigned count) {
 (void)chip;(void)name;assert(a==0 && b==0 && count==224);assert(provider_ready && !range_ready);range_ready=true;++range_adds;return 0;
}
static const char *pinctrl_dev_get_devname(struct pinctrl_dev *p) { assert(p==&provider);return "pinmux"; }
static int gpiochip_add_pingroup_range(struct gpio_chip *c,struct pinctrl_dev *p,unsigned a,const char *name) {
 (void)c;(void)p;(void)a;(void)name;assert(0);return -1;
}
static int pinctrl_get_device_gpio_range(unsigned gpio,struct pinctrl_dev **p,struct pinctrl_gpio_range **r) {
 assert(gpio==172 || gpio==21);if(!range_ready)return -EPROBE_DEFER;*p=&provider;*r=&range;return 0;
}
static bool pinctrl_ready_for_gpio_range(unsigned gpio) { (void)gpio;return range_ready; }
static void mutex_lock(int *m) { (void)m; }
static void mutex_unlock(int *m) { (void)m; }
static int gpio_to_pin(struct pinctrl_gpio_range *r,unsigned gpio) { assert(r==&range);return gpio; }
static int pinmux_request_gpio(struct pinctrl_dev *p,struct pinctrl_gpio_range *r,int pin,unsigned gpio) {
 assert(p==&provider && r==&range && pin==(int)gpio);return 0;
}
#define for_each_child_of_node(parent,node) for((node)=(parent)->child;(node);(node)=(node)->next)
static bool of_property_read_bool(struct device_node *n,const char *name) { (void)n;assert(!strcmp(name,"gpio-hog"));return true; }
static struct gpio_desc *of_parse_own_gpio(struct device_node *n,const char **name,enum gpio_lookup_flags *l,enum gpiod_flags *d) {
 *name="usb-switch";*l=GPIO_ACTIVE_HIGH;*d=GPIOD_OUT_HIGH;return &descriptors[n->line];
}
static struct gpio_chip fixture_chip;
static struct gpio_chip *gpiod_to_chip(struct gpio_desc *d) { (void)d;return &fixture_chip; }
static int gpio_chip_hwgpio(struct gpio_desc *d) { return d->line; }
static struct gpio_desc *gpiochip_request_own_desc(struct gpio_chip *c,unsigned line,const char *name) {
 (void)name;++hog_attempts;int rc=tegra_gpio_request(c,line);
 if(rc)return ERR_PTR(rc);
 return &descriptors[line==172?0:1];
}
static int gpiod_configure_flags(struct gpio_desc *d,const char *name,enum gpio_lookup_flags l,enum gpiod_flags f) {
 (void)d;(void)name;assert(l==GPIO_ACTIVE_HIGH && f==GPIOD_OUT_HIGH);++directions;return 0;
}
static void gpiochip_free_own_desc(struct gpio_desc *d) { (void)d;assert(0); }
static int desc_to_gpio(struct gpio_desc *d) { return d->line; }
static void set_bit(int bit,unsigned long *flags) { *flags |= 1UL<<bit; }
static void of_gpio_simple_xlate(void) {}
'''
main=r'''
static void reset(bool property,int kind) {
 has_range=property;soc=kind;provider_ready=range_ready=false;
 hog_attempts=directions=range_adds=puts=0;
}
static void publish_provider(void) {
 provider_ready=true;
 /* Provider's legacy fallback; actual predicate is compiled above. */
 if(!gpio_node_has_range())range_ready=true;
}
int main(void) {
 struct device_node force={"force",1,0,0},data={"data",0,&force,0};
 gpio_node.child=&data;
 struct gpio_chip chip={.of_node=&gpio_node};
 reset(false,20);
 assert(of_gpiochip_add(&chip)==0 && hog_attempts==2 && directions==0);
 publish_provider();
 assert(range_ready && directions==0 && hog_attempts==2);
 puts("PASS historical init order: GPIO registration succeeds, both hogs fail, later provider does not retry them");
 reset(true,20);
 assert(of_gpiochip_add(&chip)==-EPROBE_DEFER && hog_attempts==0 && directions==0);
 publish_provider();assert(!range_ready);
 assert(of_gpiochip_add(&chip)==0 && range_adds==1 && directions==2 && hog_attempts==2);
 puts("PASS fixed init order: defer before scan, then install range and drive both outputs");
 for(int kind=20;kind<=30;kind+=10)for(int property=0;property<2;++property) {
  reset(property,kind);publish_provider();assert(of_gpiochip_add(&chip)==0);
  assert(directions==2 && range_adds==(property?1:0) && puts==1);
 }
 reset(true,0);assert(!gpio_node_has_range() && puts==0);
 puts("PASS provider-first legacy/DT ranges on Tegra20 and Tegra30; no-provider predicate");
}
'''
# Avoid a fixture counter shadowing libc puts().
fixture=fixture.replace('range_adds,puts;','range_adds,node_puts;').replace('++puts;','++node_puts;')
main=main.replace('=puts=0','=node_puts=0').replace('&& puts==','&& node_puts==')
with tempfile.TemporaryDirectory(prefix='xoom-gpio-order-') as t:
 p=Path(t);(p/'test.c').write_text(fixture+functions+main)
 subprocess.run(['cc','-std=gnu99','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function','-O2',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('Actual OF scan/add/range, hog, pinctrl request and Tegra request functions compiled; DT/provider/descriptor/configuration dependencies controlled.')
