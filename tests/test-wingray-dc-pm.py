#!/usr/bin/env python3
"""Source gate for the legacy DC first-frame restore; no hardware claim."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
K = ROOT/'sources/kernel-donor/drivers/staging/tegra/video/dc'
dc = (K/'dc.c').read_text()
h = (K/'dc_priv.h').read_text()
assert 'pm_saved_flags[DC_N_WINDOWS]' in h and 'pm_restore_windows' in h
assert 'dc->pm_saved_flags[i] = dc->windows[i].flags;' in dc
assert 'wins[i]->flags = dc->pm_saved_flags[i];' in dc
assert 'tegra_dc_update_windows(wins, DC_N_WINDOWS)' in dc
assert 'tegra_dc_sync_windows(wins, DC_N_WINDOWS)' in dc
# update_windows takes dc->lock: it must be outside the resume lock region.
resume = dc[dc.index('static int tegra_dc_resume'):]
assert resume.index('mutex_unlock(&dc->lock);') < resume.index('tegra_dc_update_windows')
assert 'system resume scanout restore failed' in resume
print('PASS DC system resume preserves all window flags and synchronizes first frame; hardware unverified')
