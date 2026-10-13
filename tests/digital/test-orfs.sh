#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../common.sh
source "$TEST_ROOT/common.sh"
load_design_env
DATA_DIR="$TEST_ROOT/data/digital"
require_command make
require_command yosys
require_command openroad
RUN_DIR="$TEST_ROOT/run/digital-orfs"
mkdir -p "$RUN_DIR"
export DIGITAL_DATA_DIR="$DATA_DIR"
FLOW_DIR="${ORFS_DIR:?ORFS_DIR unset}/flow"
[[ -f "$FLOW_DIR/Makefile" ]] || fail "ORFS flow Makefile missing"
# Separate work directories force a real synthesis on every invocation.
WORK_DIR="$(mktemp -d "$RUN_DIR/work.XXXXXX")"
printf '%s\n' "$WORK_DIR" > "$RUN_DIR/latest-work-dir.txt"
# The image startup hook prints PDK messages; make $(shell ...) must stay clean.
# Environment is already loaded above; disable only its repeated child-shell hook.
env -u BASH_ENV make -C "$FLOW_DIR" -j 2 synth DESIGN_CONFIG="$DATA_DIR/orfs.mk" WORK_HOME="$WORK_DIR" NUM_CORES=2 YOSYS_EXE="$(command -v yosys)" OPENROAD_EXE="$(command -v openroad)" 2>&1 | tee "$RUN_DIR/orfs.log"
NETLIST="$WORK_DIR/results/nangate45/add4/base/1_synth.v"
[[ -s "$NETLIST" ]] || fail "ORFS synthesized netlist missing"
grep -q 'module add4' "$NETLIST" || fail "ORFS netlist top missing"
grep -Eq ' (AND|OR|XOR|XNOR|FA|HA|AOI|OAI|INV|BUF)[A-Z0-9_]* ' "$NETLIST" || fail "ORFS netlist has no mapped Nangate cells"
printf 'ORFS_SYNTH_PASS netlist=%s\n' "$NETLIST"
pass "ORFS small Nangate45 synthesis target"
