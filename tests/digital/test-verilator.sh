#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../common.sh
source "$TEST_ROOT/common.sh"
load_design_env
DATA_DIR="$TEST_ROOT/data/digital"
require_command verilator
require_command make
require_command g++
RUN_DIR="$TEST_ROOT/run/digital-verilator"
mkdir -p "$RUN_DIR"
verilator --cc --exe --build -j 2 --top-module add4 --Mdir "$RUN_DIR/obj_dir" "$DATA_DIR/add4.v" "$DATA_DIR/verilator_main.cpp" 2>&1 | tee "$RUN_DIR/build.log"
"$RUN_DIR/obj_dir/Vadd4" | tee "$RUN_DIR/simulation.log"
grep -Fxq 'SIMULATION_PASS vectors=256' "$RUN_DIR/simulation.log" || fail "Verilator self-check did not complete"
pass "verilator compiled exhaustive simulation"
