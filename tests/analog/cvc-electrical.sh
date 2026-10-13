#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../common.sh
source "$SCRIPT_DIR/../common.sh"
load_design_env
require_command cvc_rv
OUT_DIR="$TEST_ROOT/run/cvc-electrical"
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"
cp "$TEST_ROOT/data/analog/cvc-inverter.cdl" inverter.cdl
cp "$TEST_ROOT/data/analog/cvc-models" models
cp "$TEST_ROOT/data/analog/cvc-power" power
cp "$TEST_ROOT/data/analog/cvc.cvcrc" inverter.cvcrc
rm -f inverter.rpt inverter.rpt.error.gz
# CVC can exit zero on fatal input errors, so validate completed checking too.
cvc_rv inverter.cvcrc > cvc.stdout 2>&1 || fail "CVC execution failed: $OUT_DIR/cvc.stdout"
[[ -s inverter.rpt ]] || fail "CVC did not produce electrical-check log"
grep -q 'CVC: End:' inverter.rpt || fail "CVC did not finish electrical checking"
grep -Eq 'CVC: Total:[[:space:]]+0$' inverter.rpt || fail "CVC clean inverter has electrical errors"
grep -q '2(2) devices' inverter.rpt || fail "CVC did not check both inverter devices"
! grep -Eiq 'FATAL|unexpected error' cvc.stdout || fail "CVC reported a fatal error"
pass "CVC actual inverter voltage-aware electrical checking"
