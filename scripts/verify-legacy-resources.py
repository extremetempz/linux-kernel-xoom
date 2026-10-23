#!/usr/bin/env python3
"""Verify the compiled, non-Android Wingray carveout-only resource artifact."""
import sys
from legacy_resources import validate_artifacts

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: verify-legacy-resources.py NEW_ARTIFACT_DIRECTORY')
    validate_artifacts(sys.argv[1])
    print('PASS isolated Motorola resource profile: original reserved layout, tested wiring retained, nvmap only; no host/engine/DC/GART/IRAM ownership enabled. Hardware not tested; not an Android boot image.')
