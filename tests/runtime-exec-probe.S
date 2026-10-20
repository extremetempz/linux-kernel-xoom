/* Local diagnostic: raw execve, no libc or environment applet. */
.syntax unified
.arm
.global _start
.text
_start:
 ldr r0, =program
 ldr r1, =arguments
#if PROBE_ENV_MODE == 3
 add r2, sp, #8
#elif PROBE_ENV_MODE == 0
 ldr r3, [sp]
 add r2, sp, #4
 add r2, r2, r3, lsl #2
 add r2, r2, #4
#else
 ldr r2, =environment
#endif
 mov r7, #11
 svc #0
 rsb r0, r0, #0
 mov r7, #1
 svc #0
.data
.balign 4
program: .asciz "/bin/busybox"
applet: .asciz "sh"
option: .asciz "-c"
command: .asciz "echo RAW_EXEC_CONTROL_OK"
home: .asciz "HOME=/"
term: .asciz "TERM=linux"
.balign 4
arguments: .word program, applet, option, command, 0
environment:
#if PROBE_ENV_MODE == 2
 .word home, term
#endif
 .word 0
