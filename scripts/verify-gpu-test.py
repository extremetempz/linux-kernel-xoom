#!/usr/bin/env python3
"""Validate built GPU diagnostic resources without touching hardware."""
import sys
from gpu_test import validate_artifacts
validate_artifacts(sys.argv[1])
print('PASS fixed-clock GPU profile/config/DT/symbol gates; hardware untested')
