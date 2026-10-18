#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
target="$root/toolchains/trace-test/site-packages"
wheel="$root/toolchains/trace-test/unicorn-2.1.4.whl"
mkdir -p "$(dirname -- "$wheel")"
if [ ! -f "$wheel" ]; then
 curl -fL --max-time 120 -o "$wheel" https://files.pythonhosted.org/packages/e7/df/ded5e3684c2d7600b30cc8a7530277b8cb36644a1a9d34cade7ebb45604c/unicorn-2.1.4-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
fi
python3 - "$wheel" "$target" <<'PY'
from pathlib import Path
import hashlib,sys,zipfile
wheel=Path(sys.argv[1]);target=Path(sys.argv[2]).resolve()
assert hashlib.sha256(wheel.read_bytes()).hexdigest()=='9d6e6dea140560de4ebd8446661f7ef84a357d428c14a3ef09dacd306ec8c239'
target.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(wheel) as z:
 for name in z.namelist():assert (target/name).resolve().is_relative_to(target)
 z.extractall(target)
print('Verified Unicorn 2.1.4 installed in workspace only (Linux x86-64).')
PY
