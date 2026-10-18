/* SPDX-License-Identifier: GPL-2.0-only
 * Wingray ARM EABI only. No libc, no /dev/mem read(), no physical writes.
 * Not hardware validated. Read docs/trace-retrieval.md before using opt-in.
 */
typedef unsigned int u32;
static int syscall6(int nr, u32 a, u32 b, u32 c, u32 d, u32 e, u32 f)
{
 register u32 r0 __asm__("r0") = a;
 register u32 r1 __asm__("r1") = b;
 register u32 r2 __asm__("r2") = c;
 register u32 r3 __asm__("r3") = d;
 register u32 r4 __asm__("r4") = e;
 register u32 r5 __asm__("r5") = f;
 register u32 r7 __asm__("r7") = nr;
 __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3),
                  "r"(r4), "r"(r5), "r"(r7) : "memory", "cc");
 return (int)r0;
}
static int equal(const char *a, const char *b)
{
 while (*a && *a == *b) { a++; b++; }
 return *a == *b;
}
static int error(const char *s, u32 n, int code)
{
 syscall6(4, 2, (u32)s, n, 0, 0, 0);
 return code;
}
#define ERROR(s, code) error(s, sizeof(s)-1, code)

__attribute__((used)) int snapshot_main(u32 *stack)
{
 const char *const *argv = (const char *const *)(stack + 1);
 static const char plan[] =
  "OFFLINE DEFAULT: no device opened. Proposed mapping: 4096 bytes at "
  "0x1fe00000, PROT_READ, MAP_SHARED, O_RDONLY|O_SYNC; two 128-byte snapshots. "
  "Hardware preflight requires separate approval; see docs/trace-retrieval.md.\n";
 u32 first[32], second[32], i;
 int fd, result, rc = 0;
 volatile const u32 *mapped;
 if (stack[0] != 2 || !equal(argv[1], "--read-reserved-trace")) {
  syscall6(4, 1, (u32)plan, sizeof(plan)-1, 0, 0, 0);
  return stack[0] == 1 ? 0 : 2;
 }
 /* ARM Linux O_SYNC = 04010000 octal. mmap2 offset is in 4096-byte units. */
 fd = syscall6(5, (u32)"/dev/mem", 04010000, 0, 0, 0, 0);
 if (fd < 0) return ERROR("open failed; no fallback\n", 3);
 result = syscall6(192, 0, 4096, 1, 1, (u32)fd, 0x1fe00);
 if ((u32)result >= (u32)-4095) {
  syscall6(6, fd, 0, 0, 0, 0, 0);
  return ERROR("mmap failed; no fallback\n", 4);
 }
 mapped = (volatile const u32 *)(u32)result;
 __asm__ volatile("dmb sy" ::: "memory");
 for (i = 0; i < 32; i++) first[i] = mapped[i];
 __asm__ volatile("dmb sy" ::: "memory");
 for (i = 0; i < 32; i++) second[i] = mapped[i];
 __asm__ volatile("dmb sy" ::: "memory");
 if (syscall6(91, (u32)mapped, 4096, 0, 0, 0, 0) < 0) rc = 5;
 if (syscall6(6, fd, 0, 0, 0, 0, 0) < 0) rc = 5;
 if (rc) return ERROR("cleanup failed; snapshot withheld\n", 5);
 for (i = 0; i < 32; i++)
  if (first[i] != second[i])
   return ERROR("unstable snapshot withheld\n", 6);
 /* Write only the local stack copy, after unmapping and closing /dev/mem. */
 i = 0;
 while (i < sizeof(first)) {
  result = syscall6(4, 1, (u32)first + i, sizeof(first)-i, 0, 0, 0);
  if (result == -4) continue; /* EINTR */
  if (result <= 0 || (u32)result > sizeof(first)-i)
   return ERROR("stdout failed\n", 7);
  i += result;
 }
 return 0;
}
__asm__(".text\n.arm\n.global _start\n_start:\n"
        "mov r0, sp\nbl snapshot_main\nmov r7, #248\nsvc 0\nb .\n");
