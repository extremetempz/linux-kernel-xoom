#!/usr/bin/env python3
"""Reproduce the actual missing-directory inotify failure without any devices.

The host's real inotify syscalls check an ordinary empty temporary directory.
Generated init RC is checked for the Android /dev namespace and boot ordering;
this does not execute Android's full EventHub or prove input hardware works.
"""
import ctypes
import errno
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from android44_image import board_init, sections

rc = board_init({}).decode()
actions = dict(sections(rc))
command = 'mkdir /dev/input 0755 root input'
assert command in actions['on init']
assert command not in actions.get('on early-init', [])
assert not any('event0' in line or 'mknod' in line or '/dev/uinput' in line for line in rc.splitlines())
libc = ctypes.CDLL(None, use_errno=True)
libc.inotify_init1.argtypes = [ctypes.c_int]
libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
fd = libc.inotify_init1(os.O_CLOEXEC)
assert fd >= 0
try:
    with tempfile.TemporaryDirectory(prefix='xoom-eventhub-dir-') as directory:
        path = Path(directory)/'input'
        mask = 0x00000200 | 0x00000100  # EventHub's IN_DELETE | IN_CREATE
        assert libc.inotify_add_watch(fd, os.fsencode(path), mask) == -1
        assert ctypes.get_errno() == errno.ENOENT
        path.mkdir(mode=int(command.split()[2], 8))
        assert libc.inotify_add_watch(fd, os.fsencode(path), mask) >= 0
        assert list(path.iterdir()) == []
finally:
    os.close(fd)
print('PASS real inotify: missing directory fails ENOENT; generated Android on-init empty directory succeeds; no device nodes.')
