#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
source "$TEST_ROOT/common.sh"
load_design_env
sak-pdk gf180mcuD gf180mcu_fd_sc_mcu7t5v0
require_command librelane
RUN_DIR="$TEST_ROOT/run/librelane-gf180-smoke"
mkdir -p "$RUN_DIR"
cp "$TEST_ROOT/data/gf180-counter/"{counter.v,config.json} "$RUN_DIR/"
cd "$RUN_DIR"
# Explicit CLI flags: LibreLane's default PDK is sky130A, not environment PDK.
librelane --manual-pdk --pdk-root "$PDK_ROOT" --pdk gf180mcuD --scl gf180mcu_fd_sc_mcu7t5v0 --run-tag gf180-smoke --overwrite config.json >stdout.log 2>stderr.log
python3 - <<'PY'
import json, pathlib
for log in ['stdout.log', 'stderr.log']:
    assert 'Traceback (most recent call last)' not in pathlib.Path(log).read_text()
final = pathlib.Path('runs/gf180-smoke/final')
metrics = final / 'metrics.json'
assert metrics.is_file(), 'no final metrics.json'
data = json.loads(metrics.read_text())
assert isinstance(data, dict) and data, 'empty final metrics'
assert any(p.stat().st_size > 0 for p in final.rglob('*.gds')), 'no final GDS'
PY
pass "GF180 full LibreLane counter flow with metrics and GDS"
