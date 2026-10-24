/* SPDX-License-Identifier: GPL-2.0-only
 * Standard C/POSIX declarations used by this small client when building
 * against the owner's preserved KitKat ABI. No libc structure definitions,
 * replacement implementation, private API or host FILE layout is imported.
 * The normal Android build continues to use its platform headers.
 */
#ifndef XOOM_KITKAT_C_API_H
#define XOOM_KITKAT_C_API_H
#include <stddef.h>
int printf(const char *, ...) __attribute__((format(printf,1,2)));
int puts(const char *);
char *strstr(const char *, const char *);
int strncmp(const char *, const char *, size_t);
void *memset(void *, int, size_t);
unsigned int alarm(unsigned int);
/* Only the standard fflush(NULL) operation is used; no FILE is constructed. */
int fflush(void *);
void _exit(int) __attribute__((noreturn));
#endif
