/* SPDX-License-Identifier: GPL-2.0
 * One-shot Wingray scanout proof. Only /dev/fb0 is opened; reapply its fixed mode,
 * MMIO mappings, block-device access or persistent state. */
#include <linux/fb.h>

static int layout_ok(const struct fb_var_screeninfo *v,
                     const struct fb_fix_screeninfo *f)
{
    unsigned int rgb, end;
    if (v->xres != 1280 || v->yres != 800 || v->bits_per_pixel != 32 ||
        v->xres_virtual < 1280 || v->xres_virtual > 2048 ||
        v->yres_virtual < 800 || v->yres_virtual > 2048 ||
        v->xoffset > v->xres_virtual - 1280 ||
        v->yoffset > v->yres_virtual - 800 || v->nonstd || v->grayscale ||
        v->rotate ||
#ifdef XOOM_LEGACY_DISPLAY
        (v->pixclock != 15060 || f->smem_start != 0x2e800000 ||
         f->smem_len != 0x800000) ||
#else
        v->pixclock ||
#endif
        v->vmode != FB_VMODE_NONINTERLACED ||
        f->type != FB_TYPE_PACKED_PIXELS || f->visual != FB_VISUAL_TRUECOLOR ||
        f->line_length < v->xres_virtual * 4 || f->line_length > 8192 ||
        (f->line_length & 3) || !f->smem_start || (f->smem_start & 4095) ||
        !f->smem_len || f->smem_len > 16 * 1024 * 1024 ||
        f->mmio_len || f->mmio_start ||
        v->red.length != 8 || v->green.length != 8 || v->blue.length != 8 ||
        v->red.msb_right || v->green.msb_right || v->blue.msb_right ||
        v->red.offset > 24 || v->green.offset > 24 || v->blue.offset > 24)
        return 0;
    rgb = (255U << v->red.offset) | (255U << v->green.offset) |
          (255U << v->blue.offset);
    if (((255U << v->red.offset) & (255U << v->green.offset)) ||
        ((255U << v->red.offset) & (255U << v->blue.offset)) ||
        ((255U << v->green.offset) & (255U << v->blue.offset)))
        return 0;
    if (v->transp.length &&
        (v->transp.length != 8 || v->transp.offset > 24 ||
         v->transp.msb_right || (rgb & (255U << v->transp.offset))))
        return 0;
    /* Prior checks bound each term to well below UINT32_MAX. */
    end = (v->yoffset + 799) * f->line_length + (v->xoffset + 1280) * 4;
    return end <= f->smem_len &&
           v->yres_virtual * f->line_length <= f->smem_len;
}

static void draw_pattern(volatile unsigned char *memory,
                         const struct fb_var_screeninfo *v,
                         const struct fb_fix_screeninfo *f)
{
    static const unsigned char colors[8][3] = {
        {255,255,255}, {255,255,0}, {0,255,255}, {0,255,0},
        {255,0,255}, {255,0,0}, {0,0,255}, {0,0,0}
    };
    unsigned int y, x, color, pixel;
    for (y = 0; y < 800; ++y) {
        volatile unsigned int *row = (volatile unsigned int *)(memory +
            (y + v->yoffset) * f->line_length + v->xoffset * 4);
        for (x = 0; x < 1280; ++x) {
            color = x / 160;
            pixel = ((unsigned int)colors[color][0] << v->red.offset) |
                    ((unsigned int)colors[color][1] << v->green.offset) |
                    ((unsigned int)colors[color][2] << v->blue.offset);
            if (v->transp.length) pixel |= 255U << v->transp.offset;
            row[x] = pixel;
        }
    }
}

#ifndef DISPLAY_PATTERN_TEST
/* Linux ARM EABI, six-register syscall convention, no libc dependency. */
static long call6(long n, long a, long b, long c, long d, long e, long f)
{
    register long r0 __asm__("r0") = a;
    register long r1 __asm__("r1") = b;
    register long r2 __asm__("r2") = c;
    register long r3 __asm__("r3") = d;
    register long r4 __asm__("r4") = e;
    register long r5 __asm__("r5") = f;
    register long r7 __asm__("r7") = n;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3),
                     "r"(r4), "r"(r5), "r"(r7) : "memory", "cc");
    return r0;
}
static void finish(const char *text, unsigned int length, int status)
    __attribute__((noreturn));
static void finish(const char *text, unsigned int length, int status)
{
    call6(4, 1, (long)text, length, 0, 0, 0); /* write stdout */
    call6(1, status, 0, 0, 0, 0, 0); /* exit */
    for (;;) { }
}
static struct fb_var_screeninfo var;
static struct fb_fix_screeninfo fix;
void _start(void) __attribute__((noreturn));
void _start(void)
{
    static const char failed[] = "XOOM_PATTERN_FAILED\n";
    static const char passed[] = "XOOM_PATTERN_WRITTEN 1280x800 eight vertical bars\n";
    long fd, address, result;
    fd = call6(5, (long)"/dev/fb0", 2, 0, 0, 0, 0); /* O_RDWR */
    if (fd < 0) finish(failed, sizeof(failed)-1, 1);
    result = call6(54, fd, FBIOGET_VSCREENINFO, (long)&var, 0, 0, 0);
    if (result >= 0)
        result = call6(54, fd, FBIOGET_FSCREENINFO, (long)&fix, 0, 0, 0);
    if (result < 0 || !layout_ok(&var, &fix)) {
        call6(6, fd, 0, 0, 0, 0, 0);
        finish(failed, sizeof(failed)-1, 2);
    }
    /* No fbcon in this profile. Force the existing, validated DRM mode through
     * fb_set_par so scanout is actually enabled, without inventing timings. */
    var.activate = FB_ACTIVATE_NOW | FB_ACTIVATE_FORCE;
    result = call6(54, fd, FBIOPUT_VSCREENINFO, (long)&var, 0, 0, 0);
    if (result >= 0)
        result = call6(54, fd, FBIOGET_VSCREENINFO, (long)&var, 0, 0, 0);
    if (result >= 0)
        result = call6(54, fd, FBIOGET_FSCREENINFO, (long)&fix, 0, 0, 0);
    if (result < 0 || !layout_ok(&var, &fix)) {
        call6(6, fd, 0, 0, 0, 0, 0);
        finish(failed, sizeof(failed)-1, 5);
    }
    address = call6(192, 0, fix.smem_len, 3, 1, fd, 0); /* mmap2 RW, SHARED */
    if ((unsigned long)address >= (unsigned long)-4095) {
        call6(6, fd, 0, 0, 0, 0, 0);
        finish(failed, sizeof(failed)-1, 3);
    }
    draw_pattern((volatile unsigned char *)address, &var, &fix);
    result = call6(91, address, fix.smem_len, 0, 0, 0, 0); /* munmap */
    call6(6, fd, 0, 0, 0, 0, 0);
    if (result < 0) finish(failed, sizeof(failed)-1, 4);
    finish(passed, sizeof(passed)-1, 0);
}
#endif
