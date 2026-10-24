#!/usr/bin/env python3
"""Validate built GPU diagnostic resources without touching hardware."""
import argparse
from gpu_test import validate_artifacts,startup_cookie
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('directory');p.add_argument('--startup-trace',action='store_true');a=p.parse_args()
validate_artifacts(a.directory,startup_trace=a.startup_trace,trace_cookie=startup_cookie(a.directory) if a.startup_trace else 0x584d0049)
print('PASS GPU profile/config/DT/symbol gates; hardware untested')
