#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
load_design_env
sak-pdk sky130A
require_command ngspice
RUN_DIR="$TEST_ROOT/run/ngspice-sky130-mosfet"
mkdir -p "$RUN_DIR"
ngspice -n -b "$TEST_ROOT/data/sky130_nmos_op.spice" > "$RUN_DIR/ngspice.log" 2>&1
python3 - "$RUN_DIR/ngspice.log" <<'PY'
import math
import pathlib
import re
import sys
text = pathlib.Path(sys.argv[1]).read_text()
assert not re.search(r'(?im)^.*(?:error|unknown subckt|could not find).*$', text), text
match = re.search(r'SMOKE_ID=\s*([^\s]+)', text)
assert match, text
current = float(match[1])
assert math.isfinite(current) and 1e-6 < current < 1e-3, current
print('Sky130 NMOS current:', current)
PY
pass 'Sky130 NMOS operating point'
