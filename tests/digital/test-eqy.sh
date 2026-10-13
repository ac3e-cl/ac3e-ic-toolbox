#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../common.sh
source "$TEST_ROOT/common.sh"
load_design_env
DATA_DIR="$TEST_ROOT/data/digital"
require_command eqy
require_command yosys
RUN_DIR="$TEST_ROOT/run/digital-eqy"
mkdir -p "$RUN_DIR"
cp "$DATA_DIR/add4.v" "$DATA_DIR/add4_gate.v" "$DATA_DIR/add4.eqy" "$RUN_DIR/"
cd "$RUN_DIR"
eqy -f -j 2 -d proof add4.eqy 2>&1 | tee eqy.log
[[ -f proof/PASS ]] || fail "EQY did not prove equivalence"
pass "eqy arithmetic versus ripple-adder equivalence"
