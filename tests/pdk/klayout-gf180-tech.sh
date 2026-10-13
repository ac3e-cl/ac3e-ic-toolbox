#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
source "$TEST_ROOT/common.sh"
load_design_env
sak-pdk gf180mcuD
require_command klayout
RUN_DIR="$TEST_ROOT/run/klayout-gf180-tech"
mkdir -p "$RUN_DIR"
export GF_GDS_OUTPUT="$RUN_DIR/nfet.gds"
# The installed PCells use temporary GDS files relative to cwd.
cd "$RUN_DIR"
klayout -b -r "$TEST_ROOT/data/gf180_klayout_smoke.py" >"$RUN_DIR/klayout.log" 2>&1
test -s "$GF_GDS_OUTPUT"
pass "GF180 technology and nfet PCell geometry"
