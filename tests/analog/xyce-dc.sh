#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../common.sh
source "$SCRIPT_DIR/../common.sh"
load_design_env
require_command Xyce
require_command python3
OUT_DIR="$TEST_ROOT/run/xyce-dc"
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"
rm -f divider.cir.csv
Xyce "$TEST_ROOT/data/analog/xyce-dc.cir" -o divider.cir > xyce.log 2>&1 || fail "Xyce DC simulation failed: $OUT_DIR/xyce.log"
python3 - <<'PY'
import csv, math
from pathlib import Path
rows = list(csv.DictReader(Path('divider.cir.csv').open()))
assert len(rows) == 3, rows
for row, expected in zip(rows, (0.0, 1.0, 2.0)):
    assert math.isclose(float(row['V(IN)']), expected, abs_tol=1e-8), row
    assert math.isclose(float(row['V(OUT)']), expected / 2, abs_tol=1e-8), row
print('Xyce DC: input 0, 1, 2 V; output 0, 0.5, 1 V')
PY
pass "Xyce numeric DC divider"
