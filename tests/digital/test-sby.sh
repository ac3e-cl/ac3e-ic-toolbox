#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../common.sh
source "$TEST_ROOT/common.sh"
load_design_env
DATA_DIR="$TEST_ROOT/data/digital"
require_command sby
require_command yosys
require_command yosys-abc
RUN_DIR="$TEST_ROOT/run/digital-sby"
mkdir -p "$RUN_DIR"
cp "$DATA_DIR/add4.v" "$DATA_DIR/formal.sv" "$DATA_DIR/add4.sby" "$RUN_DIR/"
cd "$RUN_DIR"
sby -f -d proof add4.sby 2>&1 | tee sby.log
grep -Eq '^PASS([[:space:]]|$)' proof/status || fail "SBY did not prove assertions"
pass "sby ABC-PDR formal arithmetic proof"
