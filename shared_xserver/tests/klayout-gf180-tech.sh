#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
load_design_env
sak-pdk gf180mcuD
require_command klayout
RUN_DIR="$SCRIPT_DIR/run/klayout-gf180-tech"
mkdir -p "$RUN_DIR"
export GF_GDS_OUTPUT="$RUN_DIR/nfet.gds"
# The installed PCells use temporary GDS files relative to cwd.
cd "$RUN_DIR"
klayout -b -r "$SCRIPT_DIR/artifacts/gf180_klayout_smoke.py" >"$RUN_DIR/klayout.log" 2>&1
test -s "$GF_GDS_OUTPUT"
pass "GF180 technology and nfet PCell geometry"
