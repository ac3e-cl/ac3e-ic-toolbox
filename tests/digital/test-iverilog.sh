#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../common.sh
source "$TEST_ROOT/common.sh"
load_design_env
DATA_DIR="$TEST_ROOT/data/digital"
require_command iverilog
require_command vvp
RUN_DIR="$TEST_ROOT/run/digital-iverilog"
mkdir -p "$RUN_DIR"
iverilog -g2012 -s tb -o "$RUN_DIR/add4.vvp" "$DATA_DIR/add4.v" "$DATA_DIR/tb.sv" 2>&1 | tee "$RUN_DIR/compile.log"
vvp "$RUN_DIR/add4.vvp" | tee "$RUN_DIR/simulation.log"
grep -Fxq 'SIMULATION_PASS vectors=256' "$RUN_DIR/simulation.log" || fail "Icarus self-check did not complete"
pass "iverilog exhaustive simulation"
