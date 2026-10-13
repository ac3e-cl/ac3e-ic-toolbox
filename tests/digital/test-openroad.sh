#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../common.sh
source "$TEST_ROOT/common.sh"
load_design_env
DATA_DIR="$TEST_ROOT/data/digital"
require_command openroad
RUN_DIR="$TEST_ROOT/run/digital-openroad"
mkdir -p "$RUN_DIR"
export DIGITAL_DATA_DIR="$DATA_DIR" DIGITAL_RUN_DIR="$RUN_DIR"
export DIGITAL_PLATFORM_DIR="${ORFS_DIR:?ORFS_DIR unset}/flow/platforms/nangate45"
openroad -no_init -no_splash -exit "$DATA_DIR/openroad.tcl" 2>&1 | tee "$RUN_DIR/openroad.log"
openroad -no_init -no_splash -exit "$DATA_DIR/openroad-read.tcl" 2>&1 | tee -a "$RUN_DIR/openroad.log"
[[ -s "$RUN_DIR/smoke.odb" && -s "$RUN_DIR/smoke.def" ]] || fail "OpenROAD database artifacts missing"
grep -Fxq 'OPENROAD_DATABASE_PASS instances=1 nets=2' "$RUN_DIR/openroad.log" || fail "OpenROAD database round-trip failed"
pass "openroad database creation and round-trip"
