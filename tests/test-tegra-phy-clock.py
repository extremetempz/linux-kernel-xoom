#!/usr/bin/env python3
"""Compile the actual UTMI power functions with controlled MMIO/poll dependencies.

This checks error propagation and cleanup, not USB hardware or enumeration.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'sources/kernel-donor/drivers/usb/phy/phy-tegra-usb.c').read_text()
header = (root / 'sources/kernel-donor/include/linux/usb/tegra_usb_phy.h').read_text()

def block(text, prefix, semicolon=False):
    start = text.index(prefix)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + (';' if semicolon else '')

macros = source[source.index('#define ULPI_VIEWPORT'):source.index('static DEFINE_SPINLOCK')]
structures = '\n'.join([
    block(header, 'struct tegra_phy_soc_config {', True),
    block(header, 'struct tegra_utmip_config {', True),
    block(source, 'struct tegra_xtal_freq {', True),
])
functions = '\n'.join(block(source, 'static ' + signature) for signature in [
    'void utmi_phy_clk_disable(', 'int utmi_phy_clk_enable(',
    'int utmi_phy_power_on(', 'int utmi_phy_power_off(struct tegra_usb_phy *phy)\n{',
])
preamble = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
#define __iomem
#define PORT_RWC_BITS 0
#define pr_err(...) (++errors)
static unsigned int errors, pads, pad_on_calls, pad_off_calls, polls, pts_calls;
static int enable_result, disable_result;
static u32 registers[1024];
'''
stubs = r'''
#define USB_DR_MODE_PERIPHERAL 1
#define USB_DR_MODE_HOST 2
struct tegra_usb_phy {
    void *regs, *config;
    const struct tegra_xtal_freq *freq;
    const struct tegra_phy_soc_config *soc_config;
    bool is_legacy_phy;
    int mode;
};
static u32 readl(void *p) { return *(u32 *)p; }
static void writel(u32 v, void *p) { *(u32 *)p = v; }
static void udelay(unsigned int n) { assert(n == 10); }
static void set_phcd(struct tegra_usb_phy *p, bool b) { (void)p; (void)b; }
static void set_pts(struct tegra_usb_phy *p, u8 v) {
    (void)p; assert(v == 0); ++pts_calls;
}
static int utmi_wait_register(void *p, u32 mask, u32 value) {
    assert(p == (void *)registers + USB_SUSP_CTRL);
    assert(mask == USB_PHY_CLK_VALID);
    ++polls;
    return value ? enable_result : disable_result;
}
static void utmip_pad_power_on(struct tegra_usb_phy *p) {
    (void)p; ++pads; ++pad_on_calls;
}
static int utmip_pad_power_off(struct tegra_usb_phy *p) {
    (void)p; assert(pads == 1); --pads; ++pad_off_calls; return 0;
}
static int utmi_phy_power_off(struct tegra_usb_phy *phy);
'''
main = r'''
int main(void) {
    struct tegra_utmip_config config = {0};
    struct tegra_xtal_freq freq = {0};
    struct tegra_phy_soc_config soc = { .requires_usbmode_setup = true };
    const int results[] = { 0, -110, -5 };
    int cases = 0;
    for (int legacy = 0; legacy < 2; ++legacy)
    for (int mode = USB_DR_MODE_PERIPHERAL; mode <= USB_DR_MODE_HOST; ++mode)
    for (unsigned int i = 0; i < 3; ++i)
    for (int cleanup_fails = 0; cleanup_fails < 2; ++cleanup_fails) {
        memset(registers, 0, sizeof(registers));
        errors = pads = pad_on_calls = pad_off_calls = polls = pts_calls = 0;
        enable_result = results[i]; disable_result = cleanup_fails ? -5 : 0;
        struct tegra_usb_phy phy = { registers, &config, &freq, &soc,
                                    legacy, mode };
        int result = utmi_phy_power_on(&phy);
        assert(result == enable_result);
        assert(pad_on_calls == 1);
        if (result) {
            assert(pads == 0 && pad_off_calls == 1 && polls == 2);
            assert(errors == 1U + (unsigned int)cleanup_fails);
            assert(registers[USB_SUSP_CTRL / 4] & UTMIP_RESET);
            assert(registers[UTMIP_BAT_CHRG_CFG0 / 4] & UTMIP_PD_CHRG);
            assert(registers[USB_USBMODE / 4] == 0 && pts_calls == 0);
        } else {
            assert(pads == 1 && pad_off_calls == 0 && polls == 1 && errors == 0);
            assert(!(registers[USB_SUSP_CTRL / 4] & UTMIP_RESET));
            assert(registers[USB_USBMODE / 4] ==
                   (mode == USB_DR_MODE_HOST ? USB_USBMODE_HOST : USB_USBMODE_DEVICE));
            assert(pts_calls == (unsigned int)!legacy);
        }
        ++cases;
    }
    printf("PASS %d actual-source UTMI power cases; MMIO/poll/pad dependencies controlled, no hardware emulated.\n", cases);
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-utmi-test-') as temp:
    folder = Path(temp)
    c = folder / 'test.c'
    c.write_text(preamble + macros + structures + stubs + functions + main)
    subprocess.run(['cc', '-std=gnu99', '-Wall', '-Wextra', '-Werror', '-O2', str(c), '-o', str(folder / 'test')], check=True)
    subprocess.run([str(folder / 'test')], check=True)
