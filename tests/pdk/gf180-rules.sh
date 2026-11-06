#!/usr/bin/env bash
# Real installed GF180 KLayout deck, one process/thread, small layouts only.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
mkdir -p "$TEST_ROOT/run/gf180-rules"
run=$(mktemp -d "$TEST_ROOT/run/gf180-rules/run.XXXXXXXX")
python3 "$TEST_ROOT/helpers/gf180-rules.py" --output "$run"
printf 'PASS GF180 rule regressions: %s\n' "$run"
