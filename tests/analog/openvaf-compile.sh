#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../common.sh
source "$SCRIPT_DIR/../common.sh"
load_design_env
require_command openvaf
require_command python3
require_command ngspice
OUT_DIR="$TEST_ROOT/run/openvaf-compile"
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"
rm -f resistor.osdi current.dat
openvaf "$TEST_ROOT/data/analog/resistor.va" -o resistor.osdi > openvaf.log 2>&1 || fail "OpenVAF compile failed: $OUT_DIR/openvaf.log"
[[ -s resistor.osdi ]] || fail "OpenVAF produced no OSDI module"
ngspice -b "$TEST_ROOT/data/analog/openvaf-resistor.cir" > ngspice.log 2>&1 || fail "ngspice OSDI simulation failed: $OUT_DIR/ngspice.log"
python3 - <<'PY'
from pathlib import Path
import math
rows = [line.split() for line in Path('current.dat').read_text().splitlines() if line.strip()]
assert len(rows) == 1, rows
current = float(rows[0][-1])
assert math.isclose(current, -0.001, rel_tol=1e-6, abs_tol=1e-10), current
print(f'OpenVAF OSDI loaded in ngspice: I(V1)={current} A')
PY
pass "OpenVAF Verilog-A compile and ngspice numeric OSDI simulation"
