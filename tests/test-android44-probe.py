#!/usr/bin/env python3
"""Run the actual freestanding ABI gate against a host syscall recorder.

No paths are opened by the fixture. Only the ARM syscall boundary and entry-point
name are replaced; the probe's policy, control flow and wire comparisons execute.
This is a safety/control-flow test, not physical Android ABI validation. Host
UAPI scalar widths are used for syscall mocks; the separate ARM build validates
the target's ioctl encodings and wire sizes.
"""
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'diagnostic/android44-abi-probe.c').read_text()
signature = 'static long call6('
start = source.index(signature)
opening = source.index('{', start)
position, depth = opening + 1, 1
while depth:
    depth += (source[position] == '{') - (source[position] == '}')
    position += 1
source = source[:start] + source[start:opening].rstrip() + ';' + source[position:]
source = re.sub(r'\b_start\b', 'probe_start', source)

fixture = r'''
#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <linux/fs.h>
enum fault {
    NONE, WRONG_RELEASE, BLOCK_ADMITTED, BLOCK_MISSING, BLOCK_DENIED,
    RAW_OPEN_FAILED, RAW_SINGLE_ADMITTED, RAW_MULTI_ADMITTED, ROSET_ADMITTED,
    BINDER_OPEN_FAILED, BINDER_IOCTL_FAILED, BINDER_WRONG_VERSION,
    LOGGER_OPEN_FAILED, LOGGER_WRONG_VERSION, LOGGER_SHORT_WRITE,
    LOGGER_SHORT_READ, LOGGER_BAD_PAYLOAD, LOGGER_SET_FAILED,
    ASHMEM_OPEN_FAILED, ASHMEM_NAME_FAILED, ASHMEM_SIZE_FAILED,
    ASHMEM_GET_FAILED, ASHMEM_MAP_FAILED, UNIX_FAILED, UEVENT_FAILED
};
static struct {
    enum fault fault;
    unsigned index, write_opens, raw_calls, roset_calls, closes, log_writes;
    unsigned socket_calls, block_writes, nonnull_raw_commands;
    int logger_version, admitted_open_closed, last_block_fd;
    char output[2048];
    size_t output_size;
} mock;
static jmp_buf escaped;
static int exit_status;
static unsigned cases;
static unsigned private_page[1024];
'''

mock = r'''
static long call6(long n, long a, long b, long c, long d, long e, long f)
{
    (void)e; (void)f;
    switch (n) {
    case 1:
        exit_status = (int)a;
        longjmp(escaped, 1);
    case 122:
        assert((void *)a == (void *)uts);
        strcpy(uts[2], mock.fault == WRONG_RELEASE ? "wrong-kernel" :
               XOOM_ABI_RELEASE);
        return 0;
    case 5: {
        const char *path = (const char *)a;
        for (unsigned i = 0; i < sizeof(block_paths)/sizeof(block_paths[0]); ++i) {
            if (strcmp(path, block_paths[i])) continue;
            /* No truncation/creation flags may ever reach a block path. */
            assert(b == 0 || b == 1);
            assert(c == 0);
            if (b == 1) {
                assert(i == mock.write_opens++);
                if (i == mock.index) {
                    if (mock.fault == BLOCK_ADMITTED) {
                        mock.last_block_fd = 91;
                        return 91;
                    }
                    if (mock.fault == BLOCK_MISSING) return -2;
                    if (mock.fault == BLOCK_DENIED) return -13;
                }
                return -30;
            }
            assert(i == 0 && mock.write_opens == 11);
            if (mock.fault == RAW_OPEN_FAILED) return -2;
            mock.last_block_fd = 90;
            return 90;
        }
        assert(mock.write_opens == 11 && mock.raw_calls == 2 && mock.roset_calls == 1);
        if (!strcmp(path, "/dev/binder")) {
            assert(b == 2);
            return mock.fault == BINDER_OPEN_FAILED ? -2 : 10;
        }
        if (!strcmp(path, "/dev/log_main")) {
            assert(b == (2 | 0x800));
            return mock.fault == LOGGER_OPEN_FAILED ? -2 : 11;
        }
        assert(!strcmp(path, "/dev/ashmem") && b == 2);
        return mock.fault == ASHMEM_OPEN_FAILED ? -2 : 12;
    }
    case 6:
        ++mock.closes;
        if (a == 91) mock.admitted_open_closed = 1;
        return 0;
    case 54:
        if (a == 90) {
            if (c) ++mock.nonnull_raw_commands;
            assert(c == 0); /* No payload can describe a hardware command. */
            if (b == BLKROSET) {
                ++mock.roset_calls;
                return mock.fault == ROSET_ADMITTED ? 0 : -30;
            }
            ++mock.raw_calls;
            if (b == MMC_IOC_CMD)
                return mock.fault == RAW_SINGLE_ADMITTED ? 0 : -30;
            assert(b == MMC_IOC_MULTI_CMD);
            return mock.fault == RAW_MULTI_ADMITTED ? 0 : -30;
        }
        if (a == 10) {
            assert(b == BINDER_VERSION && c == (long)&version);
            if (mock.fault == BINDER_IOCTL_FAILED) return -25;
            version.protocol_version = mock.fault == BINDER_WRONG_VERSION ? 8 : 7;
            return 0;
        }
        if (a == 11) {
            if (b == LOGGER_GET_VERSION) {
                assert(c == 0);
                return mock.fault == LOGGER_WRONG_VERSION ? 99 : mock.logger_version;
            }
            assert(b == LOGGER_SET_VERSION && c == (long)&log_version);
            if (mock.fault == LOGGER_SET_FAILED) return -22;
            mock.logger_version = *(int *)c;
            assert(mock.logger_version == 2);
            return 0;
        }
        assert(a == 12);
        if (b == ASHMEM_SET_NAME) {
            assert(c == (long)ashmem_name);
            return mock.fault == ASHMEM_NAME_FAILED ? -22 : 0;
        }
        if (b == ASHMEM_SET_SIZE) {
            assert(c == 4096);
            return mock.fault == ASHMEM_SIZE_FAILED ? -22 : 0;
        }
        assert(b == ASHMEM_GET_SIZE && c == 0);
        return mock.fault == ASHMEM_GET_FAILED ? 0 : 4096;
    case 4:
        if (a == 90 || a == 91) ++mock.block_writes;
        assert(a == 1 || a == 11); /* Never a block fd, even if open admitted. */
        if (a == 1) {
            assert(mock.output_size + (size_t)c < sizeof(mock.output));
            memcpy(mock.output + mock.output_size, (void *)b, (size_t)c);
            mock.output_size += (size_t)c;
            return c;
        }
        assert(b == (long)log_message && c == sizeof(log_message)-1);
        ++mock.log_writes;
        return mock.fault == LOGGER_SHORT_WRITE ? c-1 : c;
    case 3: {
        assert(a == 11 && b == (long)log_buffer && c == sizeof(log_buffer));
        unsigned header = mock.logger_version == 1 ? 20 : 24;
        memset(log_buffer, 0, sizeof(log_buffer));
        log_buffer[0] = sizeof(log_message)-1;
        memcpy(log_buffer + header, log_message, sizeof(log_message)-1);
        if (mock.fault == LOGGER_BAD_PAYLOAD) log_buffer[header] ^= 1;
        return header + sizeof(log_message)-1 - (mock.fault == LOGGER_SHORT_READ);
    }
    case 192:
        assert(a == 0 && b == 4096 && c == 3 && d == 1 && e == 12 && f == 0);
        return mock.fault == ASHMEM_MAP_FAILED ? -12 : (long)private_page;
    case 91:
        assert(a == (long)private_page && b == 4096);
        for (unsigned i = 0; i < 1024; ++i) assert(private_page[i] == (i ^ 0x584d0030U));
        return 0;
    case 281:
        ++mock.socket_calls;
        if (mock.socket_calls == 1) {
            assert(a == 1 && b == 1 && c == 0);
            return mock.fault == UNIX_FAILED ? -1 : 13;
        }
        assert(mock.socket_calls == 2 && a == 16 && b == 2 && c == 15);
        return mock.fault == UEVENT_FAILED ? -1 : 14;
    default:
        assert(!"Unreviewed syscall attempted");
        return -38;
    }
}
static void run(enum fault fault, unsigned index, int expected)
{
    memset(&mock, 0, sizeof(mock));
    mock.fault = fault;
    mock.index = index;
    mock.logger_version = 1;
    exit_status = -999;
    if (!setjmp(escaped)) probe_start();
    assert(exit_status == expected);
    ++cases;
    assert(mock.block_writes == 0 && mock.nonnull_raw_commands == 0);
    if (fault == BLOCK_ADMITTED) {
        assert(mock.admitted_open_closed && mock.closes == 1);
        assert(mock.raw_calls == 0 && mock.roset_calls == 0 && mock.log_writes == 0);
    }
    if (fault == WRONG_RELEASE) assert(mock.write_opens == 0);
    if (expected) assert(!strstr(mock.output, "XOOM_ANDROID44_ABI_PASSED"));
    else {
        assert(mock.write_opens == 11 && mock.raw_calls == 2 && mock.roset_calls == 1);
        assert(mock.log_writes == 2 && mock.socket_calls == 2);
        assert(strstr(mock.output, "XOOM_ANDROID44_ABI_PASSED"));
    }
}
int main(void)
{
    run(NONE, 0, 0);
    run(WRONG_RELEASE, 0, 1);
    for (unsigned i = 0; i < 11; ++i) {
        run(BLOCK_ADMITTED, i, 12);
        run(BLOCK_MISSING, i, 12);
        run(BLOCK_DENIED, i, 12);
    }
    run(RAW_OPEN_FAILED, 0, 13);
    run(RAW_SINGLE_ADMITTED, 0, 14);
    run(RAW_MULTI_ADMITTED, 0, 14);
    run(ROSET_ADMITTED, 0, 15);
    run(BINDER_OPEN_FAILED, 0, 2);
    run(BINDER_IOCTL_FAILED, 0, 3);
    run(BINDER_WRONG_VERSION, 0, 3);
    run(LOGGER_OPEN_FAILED, 0, 10);
    for (enum fault f = LOGGER_WRONG_VERSION; f <= LOGGER_SET_FAILED; ++f) run(f, 0, 11);
    run(ASHMEM_OPEN_FAILED, 0, 4);
    for (enum fault f = ASHMEM_NAME_FAILED; f <= ASHMEM_GET_FAILED; ++f) run(f, 0, 5);
    run(ASHMEM_MAP_FAILED, 0, 6);
    run(UNIX_FAILED, 0, 8);
    run(UEVENT_FAILED, 0, 9);
    printf("PASS actual Android4.4 ABI probe: success and %u fault cases; all 11 unsafe write-open admissions closed then rejected; raw MMC and BLKROSET checks use only NULL payloads; no block writes.\n", cases-1);
}
'''

with tempfile.TemporaryDirectory(prefix='xoom-android44-probe-') as directory:
    path = Path(directory)
    # Select the donor's reviewed Binder/MMC interfaces without importing its
    # unsanitized internal linux/types.h into a host userspace compilation.
    for name in ('linux/android/binder.h', 'linux/mmc/ioctl.h'):
        header = path / 'include' / name
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_bytes((ROOT / 'sources/kernel-donor/include/uapi' / name).read_bytes())
    (path / 'test.c').write_text(fixture + source + mock)
    for release in ('4.4.147-wingray-android44', '4.4.147-wingray-android44-touch'):
        subprocess.run([
            'cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O2',
            '-fsanitize=undefined', f'-DXOOM_ABI_RELEASE="{release}"',
            '-I', str(path / 'include'),
            '-I', str(ROOT / 'sources/kernel-donor/drivers/staging/android'),
            str(path / 'test.c'), '-o', str(path / 'test'),
        ], check=True)
        subprocess.run([str(path / 'test')], check=True)
