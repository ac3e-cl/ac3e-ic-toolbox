#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../common.sh
source "$SCRIPT_DIR/../common.sh"
load_design_env
require_command xschem
require_command python3
OUT_DIR="$TEST_ROOT/run/xschem-netlist"
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"
rm -f xschem-resistor.spice
# Locate the installed built-in library without hardcoding its revision.
XSCHEM_PREFIX="$(cd -- "$(dirname -- "$(command -v xschem)")/.." && pwd)"
export XSCHEM_SMOKE_LIBRARY="$XSCHEM_PREFIX/share/xschem/xschem_library"
xschem -n -q -x --rcfile "$TEST_ROOT/data/analog/xschemrc" -o "$OUT_DIR" "$TEST_ROOT/data/analog/xschem-resistor.sch" > xschem.log 2>&1 || fail "Xschem headless netlisting failed: $OUT_DIR/xschem.log"
python3 - <<'PY'
from pathlib import Path
lines = Path('xschem-resistor.spice').read_text().splitlines()
resistors = [line.split() for line in lines if line.lower().startswith('rsmoke ')]
assert len(resistors) == 1, lines
r = resistors[0]
assert [n.upper() for n in r[1:3]] == ['VIN', 'VOUT'], r
assert float(r[3]) == 1234, r
print('Xschem netlist:', ' '.join(r))
PY
pass "Xschem tiny schematic generates connected resistor SPICE netlist"
