#!/usr/bin/env bash
# Exercise the public CLI with both bundled PDKs; no Ciel downloads required.
set -euo pipefail
TEST_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
load_design_env
require_command librelane
RUN_DIR="$TEST_ROOT/run/librelane-local-smoke"
mkdir -p "$RUN_DIR"
cd "$RUN_DIR"
[[ $(python --version) == Python\ 3.11.* ]] || fail 'default Python is not 3.11'
for pdk in ihp-sg13g2 gf180mcuD; do
    sak-pdk "$pdk"
    if ! librelane --smoke-test >"$pdk.log" 2>&1; then
        cat "$pdk.log" >&2
        fail "LibreLane smoke test: $pdk"
    fi
    if grep -Eq 'attempting to download|Traceback \(most recent call last\)' "$pdk.log"; then
        fail "LibreLane escaped the local isolated toolchain: $pdk"
    fi
    pass "LibreLane local smoke test: $pdk"
done
