#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../common.sh
source "$SCRIPT_DIR/../common.sh"
load_design_env
require_command netgen
OUT_DIR="$TEST_ROOT/run/netgen-lvs"
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"
rm -f match.log mismatch.log
netgen -batch lvs "$TEST_ROOT/data/analog/lvs-reference.spice divider" "$TEST_ROOT/data/analog/lvs-match.spice divider" nosetup match.log > match.stdout 2>&1 || fail "Netgen matching run failed"
netgen -batch lvs "$TEST_ROOT/data/analog/lvs-reference.spice divider" "$TEST_ROOT/data/analog/lvs-mismatch.spice divider" nosetup mismatch.log > mismatch.stdout 2>&1 || fail "Netgen mismatching run failed"
grep -Eq '^Final result: Circuits match (uniquely|correctly)\.$' match.log || fail "Netgen did not recognize matching circuits with matching pins/properties"
grep -Eq 'Circuits do not match\.|Netlists do not match\.' mismatch.log || fail "Netgen did not reject intentional topology mismatch"
pass "Netgen matching AND intentionally mismatching LVS"
