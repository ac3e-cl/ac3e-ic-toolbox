#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../common.sh
source "$TEST_ROOT/common.sh"
load_design_env
DATA_DIR="$TEST_ROOT/data/digital"
require_command yosys
require_command python3
RUN_DIR="$TEST_ROOT/run/digital-yosys"
mkdir -p "$RUN_DIR"
yosys -l "$RUN_DIR/yosys.log" -p "read_verilog $DATA_DIR/add4.v; synth -top add4; check -assert; write_json $RUN_DIR/add4.json; write_verilog -noattr $RUN_DIR/add4-synth.v"
python3 - "$RUN_DIR/add4.json" <<'PY'
import json, sys
module = json.load(open(sys.argv[1]))['modules']['add4']
assert module['cells'], 'synthesis produced no cells'
assert set(module['ports']) == {'a', 'b', 'y'}
print(f"YOSYS_SYNTH_PASS cells={len(module['cells'])}")
PY
[[ -s "$RUN_DIR/add4-synth.v" ]] || fail "Yosys netlist missing"
pass "yosys functional synthesis"
