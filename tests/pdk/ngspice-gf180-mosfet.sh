#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
source "$TEST_ROOT/common.sh"
load_design_env
sak-pdk gf180mcuD
require_command ngspice
RUN_DIR="$TEST_ROOT/run/ngspice-gf180-mosfet"
mkdir -p "$RUN_DIR"
python3 - "$TEST_ROOT/data/gf180_nmos_op.spice.in" "$RUN_DIR/device.spice" <<'PY'
import os, pathlib, sys
pathlib.Path(sys.argv[2]).write_text(pathlib.Path(sys.argv[1]).read_text().replace('@PDKPATH@', os.environ['PDKPATH']))
PY
# Ignore personal .spiceinit: GF models are explicitly included in the deck.
ngspice -n -b "$RUN_DIR/device.spice" >"$RUN_DIR/ngspice.log" 2>&1
python3 - "$RUN_DIR/ngspice.log" <<'PY'
import math, pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text()
assert not re.search(r'(?im)^.*(?:error|unknown subckt|could not find).*$', text), text
match = re.search(r'SMOKE_ID=\s*([^\s]+)', text)
assert match, text
current = float(match[1])
assert math.isfinite(current) and current > 0, current
print('GF180 measured current:', current)
PY
pass "GF180 NMOS operating point"
