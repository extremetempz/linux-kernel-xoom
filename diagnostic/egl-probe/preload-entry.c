/* SPDX-License-Identifier: GPL-2.0-only
 * Manual isolated-child entry for the existing probe. Never preload into
 * Android init, a service, or an interactive shell the user intends to keep.
 * No code runs unless XOOM_EGL_PROBE_CHILD=1 is supplied to that child.
 */
#include "kitkat-c-api.h"
char *getenv(const char *);
int xoom_egl_probe_main(void);
__attribute__((constructor)) static void xoom_probe_child(void)
{
    const char *enable = getenv("XOOM_EGL_PROBE_CHILD");
    int result;
    if (!enable || strncmp(enable, "1", 2))
        return;
    puts("XOOM_EGL_ISOLATED_CHILD_BEGIN");
    fflush(NULL);
    result = xoom_egl_probe_main();
    fflush(NULL);
    _exit(result);
}
